"""Signing in with Google (B-02, B-04, ADR-0015): start a flow, and finish it on the callback.

Accounts are found by Google's permanent subject ID only, never by email. A Google sign-in for a
person nobody linked fails, and never creates or merges an account.
"""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from qbank.core.config import Settings, without_default_port
from qbank.core.db import Database
from qbank.core.errors import Unauthenticated, ValidationFailed
from qbank.core.ids import new_id
from qbank.core.security import hash_token, new_token
from qbank.core.tenancy import NO_CONTEXT
from qbank.modules.audit.public import record_event
from qbank.modules.identity import service
from qbank.modules.identity.google import (
    GoogleClient,
    GoogleError,
    GoogleIdentity,
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


def _allowed_origin(settings: Settings, return_origin: str) -> str:
    origin = without_default_port(return_origin.strip().lower())
    if origin not in settings.allowed_origins:
        raise ValidationFailed("This web address is not allowed.", code="RETURN_ORIGIN_NOT_ALLOWED")
    return origin


def _start(
    database: Database,
    google: GoogleClient,
    origin: str,
    begin: Callable[[Session, dict[str, object]], bool],
) -> StartedFlow | None:
    """Make the flow's secrets, let ``begin`` store the flow, and build Google's address.

    ``begin`` returns False when the flow must not start; then nothing is stored.
    """
    cookie_value, state, nonce, verifier = (
        new_token(),
        new_token(),
        new_token(),
        new_code_verifier(),
    )
    flow = {
        "id": new_id(),
        "cookie": hash_token(cookie_value),
        "state": hash_token(state),
        "verifier": verifier,
        "nonce": nonce,
        "origin": origin,
    }
    with database.transaction(NO_CONTEXT) as session:
        if not begin(session, flow):
            return None
    url = google.authorization_url(
        redirect_uri=redirect_uri(origin),
        state=state,
        nonce=nonce,
        code_challenge=code_challenge(verifier),
    )
    return StartedFlow(url, cookie_value)


def start_sign_in(
    database: Database, settings: Settings, google: GoogleClient, return_origin: str
) -> StartedFlow:
    """Store a pending sign-in flow and return the Google address to go to."""
    origin = _allowed_origin(settings, return_origin)

    def begin(session: Session, flow: dict[str, object]) -> bool:
        session.execute(
            text(
                "SELECT auth_oauth_begin_sign_in(:id, :cookie, :state, :verifier, :nonce, :origin)"
            ),
            flow,
        )
        return True

    started = _start(database, google, origin, begin)
    assert started is not None  # noqa: S101  (begin never refuses a sign-in)
    return started


def start_activation(
    database: Database,
    settings: Settings,
    google: GoogleClient,
    return_origin: str,
    link_token: str,
) -> StartedFlow:
    """Check an activation link, then store a pending flow that will activate with Google.

    The link is checked now, before the person leaves for Google, and again when Google calls back.
    Any problem with it is the same ``401 LINK_INVALID`` as redeeming it with a password.
    """
    origin = _allowed_origin(settings, return_origin)

    def begin(session: Session, flow: dict[str, object]) -> bool:
        usable = session.scalar(
            text(
                "SELECT auth_oauth_begin_activation"
                "(:id, :cookie, :state, :verifier, :nonce, :origin, :token_hash)"
            ),
            {**flow, "token_hash": hash_token(link_token)},
        )
        return bool(usable)

    started = _start(database, google, origin, begin)
    if started is None:
        log.info("google_activation_refused", reason="link_not_usable")
        raise Unauthenticated(service.LINK_INVALID, code="LINK_INVALID")
    return started


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
        if flow.purpose == "SIGN_IN":
            result = _sign_in(session, settings, identity, request_id)
        elif flow.purpose == "ACTIVATE":
            result = _activate(session, settings, flow.id, identity, request_id)
        else:
            result = None  # a purpose this server cannot finish yet
    if result is None:
        log.info("google_login_failed", reason="not_allowed", purpose=flow.purpose)
        return None
    log.info("google_login_succeeded", user_id=str(result.principal.user_id), purpose=flow.purpose)
    return result


def _sign_in(
    session: Session, settings: Settings, identity: GoogleIdentity, request_id: str | None
) -> service.LoginResult | None:
    """Sign in whoever this Google account is linked to, if they still have access."""
    user_id: UUID | None = session.scalar(
        text("SELECT auth_google_user(:subject)"), {"subject": identity.subject}
    )
    return service.start_session(session, settings, user_id, request_id) if user_id else None


def _activate(
    session: Session,
    settings: Settings,
    flow_id: UUID,
    identity: GoogleIdentity,
    request_id: str | None,
) -> service.LoginResult | None:
    """Activate the invited person the flow's link belongs to, binding this Google account.

    The database function re-checks the link, the membership and the coaching, and refuses a
    Google account that is already linked to anyone. Nothing about who is activated comes from
    Google: the person is whoever the link was made for.
    """
    activated = session.execute(
        text("SELECT * FROM auth_google_activate(:flow, :subject, :email)"),
        {"flow": flow_id, "subject": identity.subject, "email": identity.email},
    ).first()
    if activated is None:
        return None
    result = service.start_session(session, settings, activated.user_id, request_id)
    record_event(
        session,
        action="ACCOUNT_ACTIVATED",
        entity_type="user",
        entity_id=activated.user_id,
        organization_id=activated.organization_id,
        actor_user_id=activated.user_id,
        request_id=request_id,
        after={"method": "google"},
    )
    return result
