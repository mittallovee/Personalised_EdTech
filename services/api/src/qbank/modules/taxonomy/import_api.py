"""Routes for the syllabus import: download the template, upload a file to preview it, read the
preview. Previewing changes nothing in the syllabus (M3 design note §4.4, C-03)."""

import base64
import binascii
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from starlette.concurrency import run_in_threadpool

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.errors import MalformedRequest
from qbank.core.idempotency import IdempotencyKeyHeader
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo
from qbank.core.permissions import Action, require
from qbank.modules.taxonomy import import_apply, import_plan
from qbank.modules.taxonomy import import_service as service
from qbank.modules.taxonomy.import_file import MAX_FILE_BYTES, ImportFileInvalid
from qbank.modules.taxonomy.import_plan import COLUMNS
from qbank.modules.taxonomy.models import CatalogueImport
from qbank.modules.taxonomy.schemas import (
    ImportCounts,
    ImportOut,
    ImportRowOut,
    ImportRowPage,
    ImportStatus,
    OneLine,
)

router = APIRouter(prefix="/api/v1/taxonomy", tags=["syllabus import"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such import in your coaching (`NOT_FOUND`)"}
}

# One example row for each kind of item; the file is UTF-8 with a byte-order mark so Excel opens it
# with the right letters.
_TEMPLATE_LINES = [
    ",".join(COLUMNS),
    "CLASS,Class 11,1,,,,,,,",
    "SUBJECT,Class 11 > Physics,1,,,,,,,",
    "CHAPTER,Class 11 > Physics > Kinematics,1,,,,,,,",
    "TOPIC,Class 11 > Physics > Kinematics > Motion in a straight line,1,,,,,,,",
    "CONCEPT,Class 11 > Physics > Newton's second law,,Newton's 2nd law,,,,,,",
    "",
]
_TEMPLATE = "\ufeff" + "\r\n".join(_TEMPLATE_LINES)


def _out(preview: CatalogueImport) -> ImportOut:
    counts = ImportCounts(
        new=preview.counts["NEW"],
        changed=preview.counts["CHANGED"],
        unchanged=preview.counts["UNCHANGED"],
        error=preview.counts["ERROR"],
    )
    return ImportOut(
        id=preview.id,
        file_name=preview.file_name,
        state=preview.state,
        counts=counts,
        can_apply=preview.state == "PREVIEWED"
        and counts.error == 0
        and 0 < counts.new + counts.changed <= import_plan.MAX_APPLY_ROWS,
        created_at=preview.created_at,
        applied_at=preview.applied_at,
    )


def _row_cursor(number: int) -> str:
    return base64.urlsafe_b64encode(b"\x02" + number.to_bytes(4, "big")).decode().rstrip("=")


def _decode_row_cursor(cursor: str) -> int:
    invalid = MalformedRequest("The page cursor is not valid. Start again from the first page.")
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
    except binascii.Error:
        raise invalid from None
    if len(raw) != 5 or raw[0] != 2:
        raise invalid
    return int.from_bytes(raw[1:], "big")


async def _read_body(request: Request) -> bytes:
    """The uploaded file, refusing to read more than the allowed size."""
    too_big = ImportFileInvalid(f"The file is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_FILE_BYTES:
        raise too_big
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_FILE_BYTES:
            raise too_big
    return bytes(body)


@router.get(
    "/import-template",
    summary="A CSV file to start an import from",
    description="One row per syllabus item or concept. Open it in Excel or any spreadsheet, fill"
    " it in, and upload it (as CSV or saved as .xlsx). Parts of a path are separated by `>`; a name"
    " that contains `>` is written with a backslash before it (`v \\> u`).",
    responses={**_DENIED, 200: {"content": {"text/csv": {}}}},
)
def import_template(principal: CurrentPrincipal) -> Response:
    require(principal, Action.MANAGE_CATALOGUES)
    return Response(
        content=_TEMPLATE,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="syllabus-template.csv"'},
    )


@router.post(
    "/imports",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a syllabus file and see what it would do",
    description=(
        "Owner and admins. Send the file itself as the request body (`.xlsx` or UTF-8 `.csv`, up"
        " to 5 MB and 20,000 rows) and its name in `file_name`. **Nothing in the syllabus"
        " changes**: the result lists every row as new, changed, unchanged or an error, with the"
        " reason for each error. A file that cannot be read at all is refused (`IMPORT_INVALID`)."
        " Send an `Idempotency-Key` so a retry returns the same preview."
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
        409: {
            "description": "The Idempotency-Key was used for a different file"
            " (`IDEMPOTENCY_KEY_REUSED`)"
        },
        422: {"description": "The file cannot be read (`IMPORT_INVALID`)"},
    },
)
async def create_import(
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    file_name: Annotated[OneLine, Query(min_length=1, max_length=200)],
    idempotency_key: Annotated[str | None, IdempotencyKeyHeader] = None,
) -> ImportOut:
    require(principal, Action.MANAGE_CATALOGUES)  # before the file is read
    data = await _read_body(request)

    def preview() -> ImportOut:
        snapshot = service.load_snapshot(database, principal.tenant_context)
        with database.transaction(principal.tenant_context) as session:
            created = service.create_preview(
                session,
                principal,
                file_name=file_name,
                data=data,
                snapshot=snapshot,
                idempotency_key=idempotency_key,
            )
            return _out(created)

    result = await run_in_threadpool(preview)
    response.headers["Location"] = f"/api/v1/taxonomy/imports/{result.id}"
    return result


@router.get(
    "/imports/{import_id}",
    summary="One import preview: its totals",
    responses={**_DENIED, **_NOT_FOUND},
)
def read_import(
    import_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> ImportOut:
    require(principal, Action.MANAGE_CATALOGUES)
    with database.transaction(principal.tenant_context) as session:
        return _out(service.get_import(session, import_id))


@router.get(
    "/imports/{import_id}/rows",
    summary="The rows of an import preview, in file order",
    description="Filter with `status=ERROR` to see only what needs fixing.",
    responses={**_DENIED, **_NOT_FOUND},
)
def read_import_rows(
    import_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    row_status: Annotated[ImportStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=32)] = None,
) -> ImportRowPage:
    require(principal, Action.MANAGE_CATALOGUES)
    after = _decode_row_cursor(cursor) if cursor is not None else 0
    with database.transaction(principal.tenant_context) as session:
        preview = service.get_import(session, import_id)
        rows, has_more = service.list_rows(preview, status=row_status, after=after, limit=limit)
        data = [ImportRowOut.model_validate(row) for row in rows]
    next_cursor = _row_cursor(data[-1].number) if has_more and data else None
    return ImportRowPage(data=data, page=PageInfo(next_cursor=next_cursor, has_more=has_more))


@router.post(
    "/imports/{import_id}/apply",
    summary="Apply an import preview to the syllabus",
    description=(
        "Owner and admins. Adds the new items and fills in the changed ones, **all or nothing**,"
        " exactly as the preview listed them. Nothing is removed, renamed, retired or restored."
        " Applying a preview that is already applied changes nothing and returns it again. Refused"
        " if any row is an error, if there is nothing to do, or if it would add or change more than"
        f" {import_plan.MAX_APPLY_ROWS:,} rows at once (`IMPORT_INVALID`); and if the syllabus has"
        " changed since the preview was made (`IMPORT_STALE`): upload the file again."
    ),
    responses={
        **_DENIED,
        **_NOT_FOUND,
        409: {"description": "The syllabus changed after the preview (`IMPORT_STALE`)"},
        422: {
            "description": "Not applicable: error rows, nothing to do, too many (`IMPORT_INVALID`)"
        },
    },
)
def apply_import(
    import_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> ImportOut:
    require(principal, Action.MANAGE_CATALOGUES)
    with database.transaction(principal.tenant_context) as session:
        applied = import_apply.apply_import(
            session, principal, import_id, request_id=request.state.request_id
        )
        return _out(applied)
