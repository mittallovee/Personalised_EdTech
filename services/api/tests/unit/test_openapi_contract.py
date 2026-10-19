"""M1 exit test T12: the committed API contract (api/openapi.json) matches the code.

Every client (web app now, mobile apps and partners later) is built from that file, so an API
change must show up as a reviewed change to it. Regenerate with ``make openapi``.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.requests import Request

from qbank.cli import main
from qbank.contract import OPENAPI_FILE, render_openapi
from qbank.core.errors import ErrorResponse, error_body
from qbank.core.openapi import install_openapi


def test_committed_contract_matches_the_code() -> None:
    assert OPENAPI_FILE.read_text(encoding="utf-8") == render_openapi(), (
        "The API changed: run `make openapi` and commit api/openapi.json"
    )


def test_export_writes_the_contract(tmp_path: Path) -> None:
    target = tmp_path / "openapi.json"

    assert main(["export-openapi", "--output", str(target)]) == 0
    assert target.read_text(encoding="utf-8") == render_openapi()


def test_check_fails_when_the_contract_is_stale(tmp_path: Path) -> None:
    stale = tmp_path / "openapi.json"
    stale.write_text("{}\n", encoding="utf-8")

    assert main(["export-openapi", "--check", "--output", str(stale)]) == 1
    assert main(["export-openapi", "--check", "--output", str(tmp_path / "missing.json")]) == 1


# --- The contract must describe what the API really does (Codex review on #6) ---------------------

CONTRACT = json.loads(render_openapi())
ERROR_REF = {"$ref": "#/components/schemas/ErrorResponse"}


def operation(method: str, path: str) -> dict[str, Any]:
    op: dict[str, Any] = CONTRACT["paths"][path][method]
    return op


def error_schema(op: dict[str, Any], status: str) -> object:
    return op["responses"][status]["content"]["application/json"]["schema"]


def test_malformed_input_is_documented_as_our_400_not_fastapis_422() -> None:
    login = operation("post", "/api/v1/auth/login")

    assert "422" not in login["responses"]
    assert error_schema(login, "400") == ERROR_REF
    assert "HTTPValidationError" not in CONTRACT["components"]["schemas"]


def test_every_error_response_uses_the_error_envelope() -> None:
    login = operation("post", "/api/v1/auth/login")

    for status in ("400", "401", "403", "429"):
        assert error_schema(login, status) == ERROR_REF


def test_signed_in_reads_need_the_session_cookie() -> None:
    me = operation("get", "/api/v1/me")

    assert me["security"] == [{"sessionCookie": []}]
    assert error_schema(me, "401") == ERROR_REF
    scheme = CONTRACT["components"]["securitySchemes"]["sessionCookie"]
    assert scheme == {"type": "apiKey", "in": "cookie", "name": "qb_session"} | {
        "description": scheme["description"]
    }


def test_signed_in_changes_need_the_cookie_and_the_csrf_header() -> None:
    logout = operation("post", "/api/v1/auth/logout")

    assert logout["security"] == [{"sessionCookie": [], "csrfHeader": []}]
    assert {"401", "403"} <= logout["responses"].keys()
    header = CONTRACT["components"]["securitySchemes"]["csrfHeader"]
    assert (header["type"], header["in"], header["name"]) == ("apiKey", "header", "X-CSRF-Token")


def test_sign_in_needs_no_credentials_but_can_be_refused_by_origin() -> None:
    login = operation("post", "/api/v1/auth/login")

    assert "security" not in login
    assert "ORIGIN_NOT_ALLOWED" in login["responses"]["403"]["description"]


def test_readiness_success_is_typed() -> None:
    ready = operation("get", "/health/ready")

    schema = ready["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/ReadyStatus"}


def test_error_envelope_model_matches_what_the_api_sends() -> None:
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": [], "state": {}})
    body = error_body(
        request, "MALFORMED_REQUEST", "x", fields=[{"path": "body.email", "code": "MISSING"}]
    )

    assert ErrorResponse.model_validate(body).model_dump() == body


def test_rate_limited_responses_declare_retry_after() -> None:
    too_many = operation("post", "/api/v1/auth/login")["responses"]["429"]

    assert too_many["headers"]["Retry-After"]["schema"] == {"type": "integer", "minimum": 1}


def test_only_fastapis_own_422_is_replaced() -> None:
    app = FastAPI()

    class Body(BaseModel):
        name: str

    @app.post("/plain")
    def plain(body: Body) -> None: ...

    @app.post(
        "/rule",
        responses={422: {"model": ErrorResponse, "description": "Breaks a business rule"}},
    )
    def rule(body: Body) -> None: ...

    install_openapi(app)
    paths = app.openapi()["paths"]

    assert set(paths["/plain"]["post"]["responses"]) >= {"400"} and (
        "422" not in paths["/plain"]["post"]["responses"]
    )
    declared = paths["/rule"]["post"]["responses"]["422"]
    assert declared["description"] == "Breaks a business rule"
    assert declared["content"]["application/json"]["schema"] == ERROR_REF


def test_every_operation_documents_the_internal_error_response() -> None:
    for item in CONTRACT["paths"].values():
        for op in item.values():
            assert error_schema(op, "500") == ERROR_REF
            assert "INTERNAL_ERROR" in op["responses"]["500"]["description"]
