"""Routes for pictures: upload one, read it back (M3 design note §5.7, D-07)."""

import math
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from starlette.concurrency import run_in_threadpool

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.errors import NotFound, TooManyRequests
from qbank.core.metrics import ASSET_EVENTS, RATE_LIMITED, org_label
from qbank.core.permissions import Action, require
from qbank.core.ratelimit import ConcurrencyGate, SlidingWindowLimiter
from qbank.core.storage import Missing, Storage
from qbank.modules.assets import service
from qbank.modules.assets.images import MAX_BYTES, ImageTooLarge, clean_image
from qbank.modules.assets.models import Asset
from qbank.modules.assets.schemas import AssetOut

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such picture in your coaching (`NOT_FOUND`)"}
}
# Decoding takes up to about a second; a refused upload may try again after this.
_BUSY_RETRY_SECONDS = 3


def _out(asset: Asset) -> AssetOut:
    return AssetOut.model_validate(
        {
            "id": asset.id,
            "kind": asset.kind,
            "content_type": asset.content_type,
            "width": asset.width,
            "height": asset.height,
            "byte_size": asset.byte_size,
            "created_at": asset.created_at,
        }
    )


async def _read_body(request: Request) -> bytes:
    """The uploaded file, refusing to read more than the allowed size."""
    too_big = ImageTooLarge(f"The picture is larger than {MAX_BYTES // (1024 * 1024)} MB.")
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BYTES:
        raise too_big
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BYTES:
            raise too_big
    return bytes(body)


@router.post(
    "/images",
    status_code=status.HTTP_201_CREATED,
    summary="Upload a picture",
    description=(
        "Any member of the coaching. Send the picture itself as the request body: PNG, JPEG or"
        " WebP, up to 10 MB and 40 megapixels. The server decides what the file is from its bytes"
        " (not its name or `Content-Type`), decodes it and stores a **re-encoded** copy, so"
        " location and camera data and anything else hidden in the file are gone; the width and"
        " height in the answer are those of the stored copy. SVG, GIF, HEIC, animated and"
        " unreadable files are refused (`IMAGE_INVALID`). Cropping is done in the browser first."
        " Reading a picture is heavy work, so a user may upload only a limited number in a short"
        " time and the server decodes only a few at once: beyond that the answer is `429`"
        " (`RATE_LIMITED`) with a `Retry-After` header."
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
        413: {"description": "More than 10 MB or 40 megapixels (`IMAGE_TOO_LARGE`)"},
        422: {"description": "Not a PNG, JPEG or WebP picture that can be read (`IMAGE_INVALID`)"},
        429: {"description": "Too many uploads, or the server is busy (`RATE_LIMITED`)"},
    },
)
async def upload_image(
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> AssetOut:
    require(principal, Action.USE_ASSETS)  # before the file is read
    limiter: SlidingWindowLimiter = request.app.state.asset_upload_limiter
    org = org_label(principal.tenant_context.organization_id)
    wait = limiter.hit(str(principal.user_id))  # before the body is read: a refusal costs nothing
    if wait > 0:
        ASSET_EVENTS.labels(org, "rejected_rate_limited").inc()
        RATE_LIMITED.labels("asset_upload").inc()
        raise TooManyRequests(
            "You have uploaded several pictures in a short time. Please wait and try again.",
            retry_after_seconds=math.ceil(wait),
        )
    data = await _read_body(request)
    gate: ConcurrencyGate = request.app.state.image_decode_gate
    storage: Storage = request.app.state.storage

    def store() -> AssetOut:
        with gate.try_enter() as entered:  # a place is held in this thread until the decode is done
            if not entered:
                ASSET_EVENTS.labels(org, "rejected_busy").inc()
                raise TooManyRequests(
                    "The server is busy reading other pictures. Please try again in a moment.",
                    retry_after_seconds=_BUSY_RETRY_SECONDS,
                )
            picture = clean_image(data)
            with database.transaction(principal.tenant_context) as session:
                asset = service.create_image(session, principal, storage, picture)
                ASSET_EVENTS.labels(org, "uploaded").inc()
                return _out(asset)

    try:
        result = await run_in_threadpool(store)
    except ImageTooLarge:
        ASSET_EVENTS.labels(org, "rejected_too_large").inc()
        raise
    response.headers["Location"] = f"/api/v1/assets/{result.id}/content"
    return result


@router.get(
    "/{asset_id}",
    summary="What is known about one picture",
    responses={**_DENIED, **_NOT_FOUND},
)
def read_asset(
    asset_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> AssetOut:
    require(principal, Action.USE_ASSETS)
    with database.transaction(principal.tenant_context) as session:
        return _out(service.get_asset(session, asset_id))


@router.get(
    "/{asset_id}/content",
    summary="The picture itself",
    description=(
        "Any member of the coaching; another coaching's picture answers 404. The `Content-Type`"
        " comes from our own record. The browser may keep the picture but must ask again each"
        " time (`Cache-Control: private, no-cache`), so a person who signs in on the same browser"
        " is checked afresh; if it has not changed (`If-None-Match`) the answer is `304`."
    ),
    responses={
        **_DENIED,
        **_NOT_FOUND,
        200: {"content": {"image/png": {}, "image/jpeg": {}, "image/webp": {}}},
        304: {"description": "The browser's copy is still the current one"},
    },
)
def read_content(
    asset_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> Response:
    require(principal, Action.USE_ASSETS)
    with database.transaction(principal.tenant_context) as session:
        asset = service.get_asset(session, asset_id)
        content_type, key, sha256 = asset.content_type, asset.storage_key, asset.sha256
    etag = f'"{sha256}"'
    # Kept by the browser but asked about every time (`no-cache`), so someone who signs in on the
    # same browser as a member of another coaching reaches the checks above instead of a cached
    # copy. A repeat request for an unchanged picture is answered 304, after those checks.
    headers = {
        "Cache-Control": "private, no-cache",
        "ETag": etag,
        "X-Content-Type-Options": "nosniff",
    }
    if _matches(request.headers.get("if-none-match"), etag):
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    storage: Storage = request.app.state.storage
    try:
        data = storage.get(key)
    except Missing as exc:
        raise NotFound("No such picture.") from exc
    return Response(
        content=data,
        media_type=content_type,
        headers={
            **headers,
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Content-Disposition": "inline",
        },
    )


def _matches(if_none_match: str | None, etag: str) -> bool:
    """Whether the browser already holds this version (`If-None-Match`, weak marks allowed)."""
    if not if_none_match:
        return False
    wanted = [part.strip().removeprefix("W/") for part in if_none_match.split(",")]
    return etag in wanted or "*" in wanted
