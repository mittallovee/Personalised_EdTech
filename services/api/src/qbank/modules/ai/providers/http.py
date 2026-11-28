"""The one way the adapters talk to a provider over HTTPS (ADR-0023).

Fixed addresses only (each adapter names its provider's base address; nothing from a client or the
database is ever used as an address), a short connect timeout and a long read timeout, no redirects,
and a cap on how much of an answer is read. Every failure becomes a ``ProviderError`` that
carries no key, request or response text.
"""

import json
from typing import Any

import httpx2

from qbank.modules.ai.providers.base import ProviderError, ProviderErrorKind

CONNECT_SECONDS = 5.0
READ_SECONDS = 120.0
MAX_RESPONSE_BYTES = 4 * 1024 * 1024


def default_client() -> httpx2.Client:
    return httpx2.Client(
        timeout=httpx2.Timeout(READ_SECONDS, connect=CONNECT_SECONDS), follow_redirects=False
    )


def kind_for_status(status: int) -> ProviderErrorKind:
    """The failure kind an HTTP status stands for (also used for a status inside a batch result)."""
    if status in (401, 403):
        return ProviderErrorKind.AUTH
    if status == 429:
        return ProviderErrorKind.RATE_LIMITED
    if status == 413:
        return ProviderErrorKind.TOO_LARGE
    if status == 408 or status >= 500:  # 529 is Anthropic's "overloaded"
        return ProviderErrorKind.UNAVAILABLE
    return ProviderErrorKind.BAD_REQUEST


def _retry_after(headers: Any) -> float | None:
    raw = headers.get("retry-after")
    try:
        seconds = float(raw)
    except TypeError, ValueError:
        return None
    return seconds if 0 <= seconds <= 3600 else None


class Http:
    """Sends one request and returns the answer as a JSON object (or, for a results file, text)."""

    def __init__(self, client: httpx2.Client | None = None) -> None:
        self._client = client or default_client()

    def get(
        self, url: str, *, headers: dict[str, str], params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return _json_object(*self._send("GET", url, headers=headers, params=params))

    def post(self, url: str, *, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        return _json_object(*self._send("POST", url, headers=headers, json=body))

    def get_text(
        self, url: str, *, headers: dict[str, str], params: dict[str, Any] | None = None
    ) -> str:
        """A file the provider serves as text (a batch's results are one JSON object per line)."""
        status, body = self._send("GET", url, headers=headers, params=params)
        try:
            return body.decode("utf-8")
        except UnicodeDecodeError:
            raise ProviderError(ProviderErrorKind.BAD_OUTPUT, status=status) from None

    def post_file(
        self,
        url: str,
        *,
        headers: dict[str, str],
        fields: dict[str, str],
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """A multipart upload of one file with some plain fields. The content type of the whole
        request (with its boundary) is made here, so ``headers`` must not carry one."""
        return _json_object(
            *self._send(
                "POST",
                url,
                headers=headers,
                data=fields,
                files={"file": (file_name, content, content_type)},
            )
        )

    def _send(self, method: str, url: str, **options: Any) -> tuple[int, bytes]:
        try:
            with self._client.stream(method, url, **options) as response:
                status = response.status_code
                declared = response.headers.get("content-length")
                if (
                    declared is not None
                    and declared.isdigit()
                    and int(declared) > MAX_RESPONSE_BYTES
                ):
                    raise ProviderError(ProviderErrorKind.TOO_LARGE, status=status)
                body = bytearray()
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise ProviderError(ProviderErrorKind.TOO_LARGE, status=status)
                retry = _retry_after(response.headers)
        except httpx2.TimeoutException:
            raise ProviderError(ProviderErrorKind.TIMEOUT) from None
        except httpx2.TransportError:
            raise ProviderError(ProviderErrorKind.UNAVAILABLE) from None
        if status >= 300:  # a redirect is never followed, so it is a failure too
            raise ProviderError(kind_for_status(status), status=status, retry_after_seconds=retry)
        return status, bytes(body)


def _json_object(status: int, body: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(body)
    except ValueError:
        raise ProviderError(ProviderErrorKind.BAD_OUTPUT, status=status) from None
    if not isinstance(parsed, dict):
        raise ProviderError(ProviderErrorKind.BAD_OUTPUT, status=status)
    return parsed


def bad_output() -> ProviderError:
    return ProviderError(ProviderErrorKind.BAD_OUTPUT)


def json_object(text: str) -> dict[str, Any]:
    """The answer text as a JSON object, or ``BAD_OUTPUT``. Models sometimes wrap JSON in a code
    fence; that is tolerated, nothing else is."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        parsed = json.loads(cleaned)
    except ValueError:
        raise bad_output() from None
    if not isinstance(parsed, dict):
        raise bad_output()
    return parsed


def count(value: object) -> int | None:
    """A token count from an answer: a non-negative whole number, else unknown."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
