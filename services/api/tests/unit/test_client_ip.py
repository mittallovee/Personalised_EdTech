"""Which address counts as "the client" for per-IP sign-in limits (ADR-0014).

Behind the web app's proxy every request arrives from the web server, and X-Forwarded-For can be
set by anyone (Next.js passes a client-supplied value through). So only a header named in
CLIENT_IP_HEADER is used, and only when the request comes from a TRUSTED_PROXIES address.
"""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from qbank.core.clientip import client_address
from qbank.core.config import AppEnv, Settings
from tests.conftest import UNREACHABLE_DB


def request_from(peer: str, headers: dict[str, str], **settings: object) -> Request:
    app = SimpleNamespace(
        state=SimpleNamespace(
            settings=Settings(app_env=AppEnv.TEST, database_url=UNREACHABLE_DB, **settings)
        )
    )
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (peer, 5000),
        "app": app,
    }
    return Request(scope)


BEHIND_CLOUDFLARE = {
    "client_ip_header": "CF-Connecting-IP",
    "trusted_proxies": ["172.16.0.0/12"],
}


def test_without_configuration_the_connection_address_is_used() -> None:
    request = request_from("172.18.0.5", {"X-Forwarded-For": "203.0.113.9"})

    assert client_address(request) == "172.18.0.5"


def test_configured_header_from_a_trusted_proxy_is_used() -> None:
    request = request_from("172.18.0.5", {"CF-Connecting-IP": "203.0.113.9"}, **BEHIND_CLOUDFLARE)

    assert client_address(request) == "203.0.113.9"


def test_header_from_an_untrusted_peer_is_ignored() -> None:
    request = request_from("198.51.100.7", {"CF-Connecting-IP": "203.0.113.9"}, **BEHIND_CLOUDFLARE)

    assert client_address(request) == "198.51.100.7"


@pytest.mark.parametrize("value", ["", "not-an-ip", "203.0.113.9, 10.0.0.1"])
def test_unusable_header_values_fall_back_to_the_connection(value: str) -> None:
    request = request_from("172.18.0.5", {"CF-Connecting-IP": value}, **BEHIND_CLOUDFLARE)

    assert client_address(request) == "172.18.0.5"


def test_x_forwarded_for_is_never_trusted_implicitly() -> None:
    request = request_from("172.18.0.5", {"X-Forwarded-For": "203.0.113.9"}, **BEHIND_CLOUDFLARE)

    assert client_address(request) == "172.18.0.5"


def test_empty_header_setting_means_none() -> None:
    settings = Settings(app_env=AppEnv.TEST, database_url=UNREACHABLE_DB, client_ip_header="")

    assert settings.client_ip_header is None


def test_trusted_proxies_must_be_networks() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env=AppEnv.TEST, database_url=UNREACHABLE_DB, trusted_proxies=["nonsense"])
