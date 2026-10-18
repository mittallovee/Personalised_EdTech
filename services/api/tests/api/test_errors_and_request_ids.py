from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qbank.core.errors import Conflict


@pytest.fixture
def app_with_test_routes(app: FastAPI) -> FastAPI:
    @app.get("/_test/conflict")
    def conflict() -> None:
        raise Conflict("Already published.", code="QUESTION_NOT_EDITABLE")

    @app.get("/_test/typed/{item_id}")
    def typed(item_id: UUID) -> dict[str, str]:
        return {"id": str(item_id)}

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("secret internal detail")

    return app


@pytest.fixture
def test_client(app_with_test_routes: FastAPI) -> TestClient:
    return TestClient(app_with_test_routes, raise_server_exceptions=False)


def test_response_carries_generated_request_id(test_client: TestClient) -> None:
    response = test_client.get("/health/live")

    assert response.headers["X-Request-ID"].startswith("req_")


def test_safe_incoming_request_id_is_echoed(test_client: TestClient) -> None:
    response = test_client.get("/health/live", headers={"X-Request-ID": "client-123"})

    assert response.headers["X-Request-ID"] == "client-123"


def test_unsafe_incoming_request_id_is_replaced(test_client: TestClient) -> None:
    response = test_client.get("/health/live", headers={"X-Request-ID": "bad id\nwith newline"})

    assert response.headers["X-Request-ID"].startswith("req_")


def test_app_error_uses_envelope_with_request_id(test_client: TestClient) -> None:
    response = test_client.get("/_test/conflict")

    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "QUESTION_NOT_EDITABLE"
    assert error["message"] == "Already published."
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_unknown_route_uses_envelope(test_client: TestClient) -> None:
    response = test_client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_malformed_input_returns_400_with_field_path(test_client: TestClient) -> None:
    response = test_client.get("/_test/typed/not-a-uuid")

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "MALFORMED_REQUEST"
    assert error["fields"][0]["path"] == "path.item_id"


def test_unexpected_error_hides_internal_details(test_client: TestClient) -> None:
    response = test_client.get("/_test/crash")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"
    assert "secret" not in response.text
    # The ID that support staff will search the logs for must also reach the client.
    assert response.headers["X-Request-ID"] == error["request_id"]
