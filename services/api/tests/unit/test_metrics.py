"""Request metrics and the /metrics page (ADR-0019): bounded labels, nothing personal."""

import socket

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from qbank.core.metrics import start_metrics_server


def sample(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


@pytest.fixture
def test_client(app: FastAPI) -> TestClient:
    @app.get("/_test/item/{item_id}")
    def item(item_id: int) -> dict[str, int]:
        return {"id": item_id}

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError("boom")

    return TestClient(app, raise_server_exceptions=False)


def test_requests_are_counted_by_route_template_and_status_class(test_client: TestClient) -> None:
    labels = {"method": "GET", "route": "/_test/item/{item_id}", "status_class": "2xx"}
    before = sample("qbank_http_requests_total", **labels)

    test_client.get("/_test/item/1")
    test_client.get("/_test/item/2")

    assert sample("qbank_http_requests_total", **labels) == before + 2  # one series, not per id
    assert sample(
        "qbank_http_request_duration_seconds_count",
        method="GET",
        route="/_test/item/{item_id}",
    )


def test_unknown_paths_share_one_label_and_errors_are_5xx(test_client: TestClient) -> None:
    unknown = {"method": "GET", "route": "unmatched", "status_class": "4xx"}
    crash = {"method": "GET", "route": "/_test/crash", "status_class": "5xx"}
    before = (
        sample("qbank_http_requests_total", **unknown),
        sample("qbank_http_requests_total", **crash),
    )

    test_client.get("/some/probe/path-1")
    test_client.get("/some/probe/path-2")
    test_client.get("/_test/crash")

    assert sample("qbank_http_requests_total", **unknown) == before[0] + 2
    assert sample("qbank_http_requests_total", **crash) == before[1] + 1


def test_the_metrics_page_is_served_on_its_own_port(test_client: TestClient) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    start_metrics_server(port)
    test_client.get("/_test/item/3")

    body = httpx2.get(f"http://127.0.0.1:{port}/metrics").text

    assert "qbank_http_requests_total" in body
    assert "qbank_db_pool_connections" in body
    assert "@" not in body  # no emails; user IDs are never labels
