"""Application errors and the one error envelope used by every API response (style guide §5)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorField(BaseModel):
    path: str  # e.g. "body.email"
    code: str  # e.g. "MISSING"


class ErrorInfo(BaseModel):
    code: str  # stable; see docs/architecture/error-codes.md
    message: str  # for people; clients must not branch on it
    request_id: str | None
    fields: list[ErrorField]
    details: dict[str, Any]


class ErrorResponse(BaseModel):
    """The one error envelope every API error uses (style guide §5); documented in OpenAPI."""

    error: ErrorInfo


class AppError(Exception):
    """Base class for errors that are safe to show to the client."""

    status_code = 400
    code = "BAD_REQUEST"

    def __init__(
        self, message: str, *, code: str | None = None, details: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details = details or {}


class MalformedRequest(AppError):
    """The request has the wrong shape in a way the schema can't check (e.g. a corrupt cursor)."""

    status_code = 400
    code = "MALFORMED_REQUEST"


class Unauthenticated(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"


class PermissionDenied(AppError):
    status_code = 403
    code = "PERMISSION_DENIED"


class NotFound(AppError):
    """Also used for resources of another coaching, so their existence is never revealed."""

    status_code = 404
    code = "NOT_FOUND"


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationFailed(AppError):
    status_code = 422
    code = "VALIDATION_FAILED"


class TooManyRequests(AppError):
    status_code = 429
    code = "RATE_LIMITED"

    def __init__(self, message: str, *, retry_after_seconds: int) -> None:
        super().__init__(message, details={"retry_after_seconds": retry_after_seconds})
        self.retry_after_seconds = retry_after_seconds


def error_body(
    request: Request,
    code: str,
    message: str,
    *,
    fields: list[dict[str, str]] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
            "fields": fields or [],
            "details": details or {},
        }
    }


def internal_error_response(request: Request) -> JSONResponse:
    """Safe 500 response for unexpected exceptions. Details go to the logs only."""
    body = error_body(request, "INTERNAL_ERROR", "Something went wrong. Please try again.")
    return JSONResponse(status_code=500, content=body)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        body = error_body(request, exc.code, exc.message, details=exc.details)
        headers = None
        if isinstance(exc, TooManyRequests):
            headers = {"Retry-After": str(exc.retry_after_seconds)}
        return JSONResponse(status_code=exc.status_code, content=body, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def handle_malformed_request(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = [
            {"path": ".".join(str(part) for part in err["loc"]), "code": err["type"].upper()}
            for err in exc.errors()
        ]
        body = error_body(request, "MALFORMED_REQUEST", "The request is not valid.", fields=fields)
        return JSONResponse(status_code=400, content=body)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else f"HTTP_{exc.status_code}"
        body = error_body(request, code, str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)
