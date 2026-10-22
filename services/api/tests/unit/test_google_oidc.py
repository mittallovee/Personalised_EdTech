"""M2 PR 8a: checking Google's answer (T19). No real Google call: a stand-in serves the keys and
the token endpoint, and signs ID tokens with a key made here."""

import time
from collections.abc import Callable
from urllib.parse import parse_qs

import httpx2
import pytest
from joserfc import jwt
from joserfc.jwk import KeySet, OctKey, RSAKey

from qbank.modules.identity.google import (
    CERTS_URL,
    TOKEN_URL,
    GoogleError,
    GoogleOidc,
    code_challenge,
    new_code_verifier,
)

CLIENT_ID = "client-123.apps.googleusercontent.com"
NONCE = "the-nonce"
REDIRECT = "http://localhost:3000/api/v1/auth/google/callback"
KEY = RSAKey.generate_key(2048, parameters={"kid": "good", "use": "sig"})
OTHER_KEY = RSAKey.generate_key(2048, parameters={"kid": "good", "use": "sig"})


def claims(**changes: object) -> dict[str, object]:
    now = int(time.time())
    base: dict[str, object] = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "1098765",
        "email": "priya@example.com",
        "email_verified": True,
        "nonce": NONCE,
        "iat": now,
        "exp": now + 600,
    }
    return {**base, **changes}


def sign(payload: dict[str, object], key: RSAKey = KEY) -> str:
    return jwt.encode({"alg": "RS256", "kid": "good"}, payload, key)


class FakeGoogle:
    """Answers the two requests the client makes and remembers what it was asked."""

    def __init__(self, id_token: str | Callable[[], str]) -> None:
        self.id_token = id_token
        self.token_requests: list[dict[str, list[str]]] = []
        self.cert_requests = 0
        self.keys = KeySet([KEY]).as_dict(private=False)

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == CERTS_URL:
            self.cert_requests += 1
            return httpx2.Response(200, json=self.keys)
        assert str(request.url) == TOKEN_URL
        self.token_requests.append(parse_qs(request.content.decode()))
        token = self.id_token() if callable(self.id_token) else self.id_token
        return httpx2.Response(200, json={"id_token": token})

    def client(self) -> GoogleOidc:
        http = httpx2.Client(transport=httpx2.MockTransport(self.handle))
        return GoogleOidc(CLIENT_ID, "the-secret", http)


def identify(oidc: GoogleOidc) -> str:
    return oidc.identify(
        code="the-code", redirect_uri=REDIRECT, code_verifier="the-verifier", nonce=NONCE
    ).subject


def test_a_valid_token_gives_the_subject_and_sends_pkce_and_the_secret() -> None:
    google = FakeGoogle(sign(claims()))
    identity = google.client().identify(
        code="the-code", redirect_uri=REDIRECT, code_verifier="the-verifier", nonce=NONCE
    )

    assert identity.subject == "1098765"
    assert identity.email == "priya@example.com"
    assert identity.email_verified is True
    [sent] = google.token_requests
    assert sent["code"] == ["the-code"]
    assert sent["code_verifier"] == ["the-verifier"]
    assert sent["redirect_uri"] == [REDIRECT]
    assert sent["client_secret"] == ["the-secret"]
    assert sent["grant_type"] == ["authorization_code"]


@pytest.mark.parametrize(
    "bad",
    [
        claims(aud="someone-elses-client"),
        claims(iss="https://evil.example.com"),
        claims(exp=int(time.time()) - 60),
        claims(nonce="another-nonce"),
        {k: v for k, v in claims().items() if k != "nonce"},
        {k: v for k, v in claims().items() if k != "sub"},
        claims(sub=""),
    ],
    ids=["audience", "issuer", "expired", "nonce", "no-nonce", "no-subject", "empty-subject"],
)
def test_a_token_that_breaks_a_rule_is_refused(bad: dict[str, object]) -> None:
    with pytest.raises(GoogleError):
        identify(FakeGoogle(sign(bad)).client())


def test_a_token_signed_by_another_key_is_refused() -> None:
    with pytest.raises(GoogleError):
        identify(FakeGoogle(sign(claims(), OTHER_KEY)).client())


def test_a_token_signed_with_a_shared_secret_is_refused() -> None:
    secret = OctKey.import_key("x" * 64)
    forged = jwt.encode({"alg": "HS256", "kid": "good"}, claims(), secret)
    with pytest.raises(GoogleError):
        identify(FakeGoogle(forged).client())


def test_an_unsigned_token_is_refused() -> None:
    unsigned = "eyJhbGciOiJub25lIiwia2lkIjoiZ29vZCJ9.eyJzdWIiOiIxIn0."
    with pytest.raises(GoogleError):
        identify(FakeGoogle(unsigned).client())


def test_garbage_instead_of_a_token_is_refused() -> None:
    with pytest.raises(GoogleError):
        identify(FakeGoogle("not-a-token").client())


def test_a_failed_exchange_is_refused() -> None:
    http = httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(400)))
    with pytest.raises(GoogleError):
        identify(GoogleOidc(CLIENT_ID, "the-secret", http))


def test_google_keys_are_fetched_once_and_kept() -> None:
    google = FakeGoogle(sign(claims()))
    oidc = google.client()
    identify(oidc)
    identify(oidc)
    assert google.cert_requests == 1


def test_a_rotated_key_is_noticed_once_the_minimum_wait_has_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    new_key = RSAKey.generate_key(2048, parameters={"kid": "good", "use": "sig"})
    google = FakeGoogle(sign(claims(), new_key))  # signed with a key we have not fetched yet
    oidc = google.client()
    with pytest.raises(GoogleError):
        identify(oidc)  # keys were fetched a moment ago: no second fetch yet
    assert google.cert_requests == 1

    monkeypatch.setattr("qbank.modules.identity.google._CERTS_MIN_REFETCH_SECONDS", 0)
    google.keys = KeySet([new_key]).as_dict(private=False)
    assert identify(oidc) == "1098765"
    assert google.cert_requests == 2


def test_the_authorization_address_carries_pkce_state_and_nonce() -> None:
    url = GoogleOidc(CLIENT_ID, "s").authorization_url(
        redirect_uri=REDIRECT, state="st", nonce="no", code_challenge="cc"
    )
    query = {k: v[0] for k, v in parse_qs(url.split("?", 1)[1]).items()}
    assert url.startswith("https://accounts.google.com/")
    assert query["client_id"] == CLIENT_ID
    assert query["redirect_uri"] == REDIRECT
    assert query["response_type"] == "code"
    assert (query["state"], query["nonce"]) == ("st", "no")
    assert (query["code_challenge"], query["code_challenge_method"]) == ("cc", "S256")


def test_code_challenge_is_the_rfc_7636_example() -> None:
    # RFC 7636 appendix B.
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert code_challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_new_verifiers_are_long_and_different() -> None:
    first, second = new_code_verifier(), new_code_verifier()
    assert first != second
    assert 43 <= len(first) <= 128
