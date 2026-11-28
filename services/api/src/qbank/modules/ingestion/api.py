"""Routes for uploaded documents (M6 design note §6, G-01, G-09).

The API only receives the bytes, decides the kind from the first few of them, keeps the original and
queues a job. It never parses a document: that happens in the sandboxed worker (ADR-0024).
"""

import math
from typing import Annotated, Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from starlette.concurrency import run_in_threadpool

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.errors import NotFound, TooManyRequests
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.core.permissions import Action, require
from qbank.core.ratelimit import SlidingWindowLimiter
from qbank.core.storage import Missing, Storage
from qbank.modules.ingestion import service
from qbank.modules.ingestion.filetype import (
    MAX_DOCUMENT_BYTES,
    DocumentInvalid,
    DocumentTooLarge,
    sniff,
)
from qbank.modules.ingestion.models import IngestFile
from qbank.modules.ingestion.schemas import IngestFileOut, IngestFilePage, State

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such document of yours in this coaching (`NOT_FOUND`)"}
}
_CONTENT_TYPE_BY_KIND = {
    "PDF": "application/pdf",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "HEIC": "image/heic",
}


def _out(row: IngestFile, duplicate_of: UUID | None = None) -> IngestFileOut:
    return IngestFileOut.model_validate(
        {
            "id": row.id,
            "file_name": row.file_name,
            "kind": row.kind,
            "byte_size": row.byte_size,
            "state": row.state,
            "page_count": row.page_count,
            "error_code": row.error_code,
            "uploaded_by": row.uploaded_by,
            "duplicate_of": duplicate_of,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
    )


async def _read_body(request: Request) -> bytes:
    """The uploaded file, refusing to read more than the largest document allowed."""
    too_big = DocumentTooLarge(
        f"The file is larger than {MAX_DOCUMENT_BYTES // (1024 * 1024)} MB (10 MB for a picture)."
    )
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_DOCUMENT_BYTES:
        raise too_big
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_DOCUMENT_BYTES:
            raise too_big
    return bytes(body)


@router.post(
    "/files",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document (G-01)",
    description=(
        "Any member. Send the file itself as the request body and its name as `file_name`: PDF,"
        " Word (.docx), JPEG, PNG, WebP or HEIC, up to 50 MB (10 MB for a picture). The kind is"
        " decided from the file's first bytes, never from its name or `Content-Type`; anything"
        " else is refused (`INGEST_FILE_INVALID`). The server keeps the original exactly as sent"
        " and queues a job; it does not open the file. A person may send a limited number of files"
        " in a short time, and a coaching may have only so many waiting to be read"
        " (`INGEST_TOO_MANY_IN_FLIGHT`). `duplicate_of` names an earlier file with exactly the"
        " same bytes; the new one is kept anyway."
    ),
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
    responses={
        **_DENIED,
        409: {"description": "Too many documents are waiting (`INGEST_TOO_MANY_IN_FLIGHT`)"},
        413: {"description": "Too large (`INGEST_FILE_TOO_LARGE`)"},
        422: {"description": "Not a kind of file we read (`INGEST_FILE_INVALID`)"},
        429: {"description": "Too many uploads in a short time (`RATE_LIMITED`)"},
    },
)
async def upload_file(
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    file_name: Annotated[str, Query(min_length=1, max_length=400)],
) -> IngestFileOut:
    require(principal, Action.USE_INGEST)  # before the file is read
    limiter: SlidingWindowLimiter = request.app.state.ingest_upload_limiter
    wait = limiter.hit(str(principal.user_id))  # a refusal costs nothing: the body is not read
    if wait > 0:
        raise TooManyRequests(
            "You have uploaded several documents in a short time. Please wait and try again.",
            retry_after_seconds=math.ceil(wait),
        )
    data = await _read_body(request)
    detected = sniff(data[:16])
    if detected is None:
        raise DocumentInvalid("This is not a PDF, Word (.docx), JPEG, PNG, WebP or HEIC file.")
    if len(data) > detected.max_bytes:
        raise DocumentTooLarge(
            f"A {detected.kind} file can be at most {detected.max_bytes >> 20} MB."
        )
    storage: Storage = request.app.state.storage
    in_flight: int = request.app.state.settings.ingest_files_in_flight
    request_id: str | None = getattr(request.state, "request_id", None)

    def store() -> IngestFileOut:
        with database.transaction(principal.tenant_context) as session:
            row, same = service.create_file(
                session,
                principal,
                storage,
                data=data,
                detected=detected,
                file_name=file_name,
                in_flight_limit=in_flight,
                request_id=request_id,
            )
            return _out(row, same)

    return await run_in_threadpool(store)


@router.get(
    "/files",
    summary="Your uploaded documents, newest first",
    description="A member sees their own uploads; the Owner and admins see everyone's.",
    responses=_DENIED,
)
def list_files(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    state: Annotated[State | None, Query(description="Only files in this state.")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> IngestFilePage:
    require(principal, Action.USE_INGEST)
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
        rows, more = service.list_files(session, principal, limit=limit, after=after, state=state)
        data = [_out(row) for row in rows]
        next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id) if more else None
    return IngestFilePage(data=data, page=PageInfo(next_cursor=next_cursor, has_more=more))


@router.get(
    "/files/{file_id}",
    summary="One uploaded document",
    responses={**_DENIED, **_NOT_FOUND},
)
def read_file(
    file_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> IngestFileOut:
    require(principal, Action.USE_INGEST)
    with database.transaction(principal.tenant_context) as session:
        return _out(service.get_file(session, principal, file_id))


@router.get(
    "/files/{file_id}/original",
    summary="The original file, as it was sent (G-09)",
    description=(
        "Same visibility as the file. It is always a **download** with a content type fixed by the"
        " server from the kind (never from the upload), `X-Content-Type-Options: nosniff` and a"
        " sandboxing policy, so a stored file can never run in the browser. The review screens show"
        " the server's own page pictures, not this file."
    ),
    responses={**_DENIED, **_NOT_FOUND, 200: {"content": {"application/octet-stream": {}}}},
)
def read_original(
    file_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> Response:
    require(principal, Action.USE_INGEST)
    with database.transaction(principal.tenant_context) as session:
        row = service.get_file(session, principal, file_id)
        key, kind, name, sha = row.storage_key, row.kind, row.file_name, row.sha256
    storage: Storage = request.app.state.storage
    try:
        data = storage.get(key)
    except Missing as exc:
        raise NotFound("The original is no longer available.") from exc
    return Response(
        content=data,
        media_type=_CONTENT_TYPE_BY_KIND[kind],
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(name, safe='')}",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "private, no-cache",
            "ETag": f'"{sha}"',
        },
    )
