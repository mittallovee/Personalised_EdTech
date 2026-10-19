"""Make the generated OpenAPI contract describe what the API really does (style guide §5, §7).

FastAPI documents each route from its code, but some behaviour is shared and lives in middleware
and error handlers. This adds it to every operation, so new routes are documented correctly
without extra work:

- malformed input is our ``400 MALFORMED_REQUEST``, not FastAPI's default 422;
- every error response uses the ``ErrorResponse`` envelope;
- signed-in operations need the session cookie, and changes also need the CSRF header;
- changes can be refused with 403 (Origin allow-list, CSRF header).
"""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from qbank.core.auth import CSRF_HEADER
from qbank.core.errors import ErrorResponse
from qbank.core.origin import SAFE_METHODS

SESSION_SCHEME = "sessionCookie"  # declared by core.auth.require_principal
CSRF_SCHEME = "csrfHeader"

_ERROR_CONTENT = {
    "application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}},
}


def install_openapi(app: FastAPI) -> None:
    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = _describe_shared_behaviour(
                get_openapi(title=app.title, version=app.version, routes=app.routes)
            )
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]


def _describe_shared_behaviour(schema: dict[str, Any]) -> dict[str, Any]:
    components = schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    for name in ("HTTPValidationError", "ValidationError"):  # replaced by our 400 below
        schemas.pop(name, None)
    error_schema = ErrorResponse.model_json_schema(ref_template="#/components/schemas/{model}")
    schemas.update(error_schema.pop("$defs", {}))
    schemas["ErrorResponse"] = error_schema
    components.setdefault("securitySchemes", {})[CSRF_SCHEME] = {
        "type": "apiKey",
        "in": "header",
        "name": CSRF_HEADER,
        "description": "The csrf_token from the sign-in response; required on every change.",
    }

    for path_item in schema.get("paths", {}).values():
        for method, operation in path_item.items():
            _describe_operation(method.upper(), operation)
    components["schemas"] = dict(sorted(schemas.items()))
    return schema


def _describe_operation(method: str, operation: dict[str, Any]) -> None:
    responses: dict[str, Any] = operation.setdefault("responses", {})
    if responses.pop("422", None) is not None:
        responses["400"] = {"description": "The request is not valid (`MALFORMED_REQUEST`)"}

    signed_in = any(SESSION_SCHEME in need for need in operation.get("security", []))
    is_change = method not in SAFE_METHODS
    if signed_in:
        responses.setdefault("401", {"description": "Not signed in (`UNAUTHENTICATED`)"})
        if is_change:
            operation["security"] = [{SESSION_SCHEME: [], CSRF_SCHEME: []}]
    if is_change:
        refusals = "`ORIGIN_NOT_ALLOWED` (sent from another website)"
        if signed_in:
            refusals += ", `CSRF_TOKEN_INVALID` (missing or wrong X-CSRF-Token)"
        responses.setdefault("403", {"description": f"Refused: {refusals}"})

    for status, response in responses.items():
        if status.isdigit() and int(status) >= 400 and "content" not in response:
            response["content"] = _ERROR_CONTENT
    operation["responses"] = dict(sorted(responses.items()))
