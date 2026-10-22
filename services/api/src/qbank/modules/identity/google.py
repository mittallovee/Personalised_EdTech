"""Talking to Google for sign-in: the address to send people to, and checking who came back.

OpenID Connect "authorization code" flow with PKCE (ADR-0015). Every address here is a fixed
constant, so nothing a caller sends can make the server fetch somewhere else.
"""

import base64
import hashlib
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

import httpx2
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105  (an address, not a secret)
CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ["https://accounts.google.com", "accounts.google.com"]
_CERTS_MAX_AGE_SECONDS = 3600
_CERTS_MIN_REFETCH_SECONDS = 60
_TIMEOUT_SECONDS = 10.0


class GoogleError(Exception):
    """Google did not give a valid, trustworthy answer. Never shown to the person."""


@dataclass(frozen=True, slots=True)
class GoogleIdentity:
    subject: str  # Google's permanent ID for the account: the only thing accounts are matched on
    email: str | None
    email_verified: bool


class GoogleClient(Protocol):
    def authorization_url(
        self, *, redirect_uri: str, state: str, nonce: str, code_challenge: str
    ) -> str: ...

    def identify(
        self, *, code: str, redirect_uri: str, code_verifier: str, nonce: str
    ) -> GoogleIdentity: ...


def new_code_verifier() -> str:
    """The PKCE secret (RFC 7636): 43 to 128 URL-safe characters, kept on the server."""
    return secrets.token_urlsafe(64)


def code_challenge(code_verifier: str) -> str:
    """What Google is told up front, so only whoever holds the verifier can finish the flow."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class GoogleOidc:
    """The real thing. Tests use a stand-in with the same two methods."""

    def __init__(
        self, client_id: str, client_secret: str, http: httpx2.Client | None = None
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = http or httpx2.Client(timeout=_TIMEOUT_SECONDS)
        self._keys: KeySet | None = None
        self._keys_fetched_at = 0.0
        self._lock = threading.Lock()

    def authorization_url(
        self, *, redirect_uri: str, state: str, nonce: str, code_challenge: str
    ) -> str:
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email",
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "prompt": "select_account",
            }
        )
        return f"{AUTHORIZATION_URL}?{query}"

    def identify(
        self, *, code: str, redirect_uri: str, code_verifier: str, nonce: str
    ) -> GoogleIdentity:
        """Swap the code for Google's ID token and check it: signature, issuer, audience, expiry
        and nonce. Any problem raises ``GoogleError``."""
        try:
            response = self._http.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            id_token = response.json()["id_token"]
        except (httpx2.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise GoogleError("token exchange failed") from exc
        if not isinstance(id_token, str):
            raise GoogleError("no ID token")
        claims = self._verified_claims(id_token, nonce)
        subject = claims.get("sub")
        if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
            raise GoogleError("no subject")
        email = claims.get("email")
        return GoogleIdentity(
            subject=subject,
            email=email if isinstance(email, str) else None,
            email_verified=claims.get("email_verified") is True,
        )

    def _verified_claims(self, id_token: str, nonce: str) -> dict[str, object]:
        try:
            token = self._decode(id_token, self._signing_keys())
        except JoseError:
            # Google may have rotated its keys since we fetched them: look once more, but not
            # more often than once a minute, so a stream of bad tokens cannot make us hammer Google.
            if time.monotonic() - self._keys_fetched_at < _CERTS_MIN_REFETCH_SECONDS:
                raise GoogleError("ID token not accepted") from None
            try:
                token = self._decode(id_token, self._signing_keys(refresh=True))
            except JoseError as exc:
                raise GoogleError("ID token not accepted") from exc
        try:
            JWTClaimsRegistry(
                iss={"essential": True, "values": ISSUERS},
                aud={"essential": True, "value": self._client_id},
                exp={"essential": True},
                iat={"essential": True},
                sub={"essential": True},
                nonce={"essential": True, "value": nonce},
            ).validate(token.claims)
        except JoseError as exc:
            raise GoogleError("ID token not accepted") from exc
        return dict(token.claims)

    @staticmethod
    def _decode(id_token: str, keys: KeySet) -> jwt.Token:
        # Only Google's signing algorithm is accepted: never "none", never a shared secret.
        return jwt.decode(id_token, keys, algorithms=["RS256"])

    def _signing_keys(self, *, refresh: bool = False) -> KeySet:
        """Google's public keys, kept for an hour (they change rarely)."""
        with self._lock:
            stale = time.monotonic() - self._keys_fetched_at > _CERTS_MAX_AGE_SECONDS
            if self._keys is None or stale or refresh:
                try:
                    response = self._http.get(CERTS_URL)
                    response.raise_for_status()
                    self._keys = KeySet.import_key_set(response.json())
                except (httpx2.HTTPError, ValueError, JoseError) as exc:
                    raise GoogleError("could not fetch Google's keys") from exc
                self._keys_fetched_at = time.monotonic()
            return self._keys
