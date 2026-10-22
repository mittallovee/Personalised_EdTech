"""Signing in with Google (B-02, B-04, ADR-0015): start a flow, and finish it on the callback.

Accounts are found by Google's permanent subject ID only, never by email. A Google sign-in for a
person nobody linked fails, and never creates or merges an account.
"""

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy import text

from qbank.core.config import Settings, without_default_port
from qbank.core.db import Database
from qbank.core.errors import ValidationFailed
from qbank.core.ids import new_id
from qbank.core.security import hash_token, new_token
from qbank.core.tenancy import NO_CONTEXT
from qbank.modules.identity import service
from qbank.modules.identity.google import (
    GoogleClient,
    GoogleError,
    code_challenge,
    new_code_verifier,
)

log = structlog.get_logger("qbank.identity")

CALLBACK_PATH = "/api/v1/auth/google/callback"


@dataclass(frozen=True, slots=True)
class StartedFlow:
    authorization_url: str  # where to send the person
    cookie_value: str  # goes in the pending-flow cookie; only its hash is stored


def redirect_uri(return_origin: str) -> str:
    return f"{return_origin}{CALLBACK_PATH}"


def start_sign_in(
    database: Database, settings: Settings, google: GoogleClient, return_origin: str
) -> StartedFlow:
    """Store a pending sign-in flow and return the Google address to go to."""
    origin = without_default_port(return_origin.strip().lower())
    if origin not in settings.allowed_origins:
        raise ValidationFailed("This web address is not allowed.", code="RETURN_ORIGIN_NOT_ALLOWED")
    cookie_value, state, nonce, verifier = (
        new_token(),
        new_token(),
        new_token(),
        new_code_verifier(),
    )
    with database.transaction(NO_CONTEXT) as session:
        session.execute(
            text(
                "SELECT auth_oauth_begin_sign_in(:id, :cookie, :state, :verifier, :nonce, :origin)"
            ),
            {
                "id": new_id(),
                "cookie": hash_token(cookie_value),
                "state": hash_token(state),
                "verifier": verifier,
                "nonce": nonce,
                "origin": origin,
            },
        )
    url = google.authorization_url(
        redirect_uri=redirect_uri(origin),
        state=state,
        nonce=nonce,
        code_challenge=code_challenge(verifier),
    )
    return StartedFlow(url, cookie_value)


def finish(
    database: Database,
    settings: Settings,
    google: GoogleClient,
    *,
    cookie: str | None,
    state: str | None,
    code: str | None,
    request_id: str | None,
) -> service.LoginResult | None:
    """Complete a flow Google has called back about. Returns the new session, or None for any
    failure (one outcome, so the person cannot learn why). Nothing is changed on failure.

    The flow is used up first, in its own transaction: a replay, a wrong ``state`` or a denied
    consent can never be retried. Google is asked only after that. The person's right to sign in is
    then checked afresh, because minutes may have passed (a removal or suspension stops the flow).
    """
    if not cookie or not state:
        log.info("google_login_failed", reason="missing_cookie_or_state")
        return None
    with database.transaction(NO_CONTEXT) as session:
        flow = session.execute(
            text("SELECT * FROM auth_oauth_take(:cookie, :state)"),
            {"cookie": hash_token(cookie), "state": hash_token(state)},
        ).first()
    if flow is None:
        log.info("google_login_failed", reason="no_usable_flow")
        return None
    if flow.purpose != "SIGN_IN":
        log.info("google_login_failed", reason="unsupported_purpose")
        return None
    if not code:
        log.info("google_login_failed", reason="no_code")  # e.g. the person pressed "Cancel"
        return None
    try:
        identity = google.identify(
            code=code,
            redirect_uri=redirect_uri(flow.return_origin),
            code_verifier=flow.code_verifier,
            nonce=flow.nonce,
        )
    except GoogleError as exc:
        log.info("google_login_failed", reason="google_refused", detail=str(exc))
        return None

    with database.transaction(NO_CONTEXT) as session:
        user_id: UUID | None = session.scalar(
            text("SELECT auth_google_user(:subject)"), {"subject": identity.subject}
        )
        result = service.start_session(session, settings, user_id, request_id) if user_id else None
    if result is None:
        log.info("google_login_failed", reason="not_linked_or_no_access")
        return None
    log.info("google_login_succeeded", user_id=str(result.principal.user_id))
    return result
