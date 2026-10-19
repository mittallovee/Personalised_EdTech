"""The client's address, used to rate-limit sign-in per IP (ADR-0014).

Requests reach the API through the web app's proxy (and, when hosted, a tunnel or load balancer),
so the connection address is the proxy's. ``X-Forwarded-For`` cannot be used: anyone can send it
and Next.js passes a client-supplied value through. Instead a deployment may name one header that
its edge sets and clients cannot forge (``CLIENT_IP_HEADER``, e.g. Cloudflare's
``CF-Connecting-IP``); it is believed only on connections from ``TRUSTED_PROXIES``.
"""

from ipaddress import ip_address

from fastapi import Request

from qbank.core.config import Settings


def client_address(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    settings: Settings = request.app.state.settings
    if settings.client_ip_header is None or not _is_trusted(peer, settings):
        return peer
    try:
        return str(ip_address(request.headers.get(settings.client_ip_header, "").strip()))
    except ValueError:  # missing or malformed: fall back to the connection
        return peer


def _is_trusted(peer: str, settings: Settings) -> bool:
    try:
        address = ip_address(peer)
    except ValueError:
        return False
    return any(address in network for network in settings.trusted_proxies)
