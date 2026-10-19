"""Refuse changes that a browser sends on behalf of another website (owner decision, 19 Oct 2026).

Defence in depth against cross-site request forgery, including "login CSRF" (a malicious page
signing the victim's browser in to the attacker's account). The other layers are SameSite cookies,
the X-CSRF-Token header on signed-in changes, JSON-only bodies and no CORS permission.

Browsers send ``Origin`` with every cross-site POST/PUT/PATCH/DELETE; we fall back to ``Referer``
when it is missing. A request with neither header is not from a browser acting for a victim, so
it continues to the normal authentication checks (mobile apps and partners use tokens, ADR-0006).
"""

from collections.abc import Awaitable, Callable, Iterable
from urllib.parse import urlsplit

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from qbank.core.errors import error_body

log = structlog.get_logger("qbank.origin")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_UNKNOWN = "null"  # what browsers send for opaque origins; never allowed


def request_origin(request: Request) -> str | None:
    """The web origin the request came from, or None when no browser header says."""
    origin = request.headers.get("origin")
    if origin is not None:
        return origin.lower()
    referer = request.headers.get("referer")
    if not referer:
        return None
    try:
        parts = urlsplit(referer)
        port = parts.port
    except ValueError:
        return _UNKNOWN
    if not parts.scheme or not parts.hostname:
        return _UNKNOWN
    return f"{parts.scheme}://{parts.hostname}" + (f":{port}" if port else "")


def install_origin_check(app: FastAPI, allowed_origins: Iterable[str]) -> None:
    allowed = frozenset(allowed_origins)

    @app.middleware("http")
    async def origin_check(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method not in SAFE_METHODS:
            origin = request_origin(request)
            if origin is not None and origin not in allowed:
                log.warning(
                    "origin_refused",
                    origin=origin[:200],
                    method=request.method,
                    path=request.url.path,
                )
                body = error_body(
                    request,
                    "ORIGIN_NOT_ALLOWED",
                    "This change was not sent from an allowed web address.",
                )
                return JSONResponse(status_code=403, content=body)
        return await call_next(request)
