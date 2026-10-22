"""Signing in with Google (B-02, B-04, ADR-0015): start a flow, and finish it on the callback.

Accounts are found by Google's permanent subject ID only, never by email. A Google sign-in for a
person nobody linked fails, and never creates or merges an account.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.config import Settings, without_default_port
from qbank.core.db import Database
from qbank.core.errors import (
    Conflict,
    NotFound,
    PermissionDenied,
    Unauthenticated,
    ValidationFailed,
)
from qbank.core.ids import new_id
from qbank.core.security import hash_token, new_token, verify_password
from qbank.core.tenancy import NO_CONTEXT, TenantContext, apply_tenant_context
from qbank.modules.audit.public import record_event
from qbank.modules.identity import service
from qbank.modules.identity.google import (
    GoogleClient,
    GoogleError,
    GoogleIdentity,
    code_challenge,
    new_code_verifier,
)
from qbank.modules.identity.schemas import GoogleStatus, LoginMethods

log = structlog.get_logger("qbank.identity")

CALLBACK_PATH = "/api/v1/auth/google/callback"
# Where the browser lands after Google calls back. Relative, so it stays on the web address the
# person is already using (the web app proxies /api, ADR-0014).
SIGNED_IN_PATH = "/"
SIGN_IN_FAILED_PATH = "/login?google=failed"
ACTIVATION_FAILED_PATH = "/activate?google=failed"
LINKED_PATH = "/profile?google=linked"
# The `state` Google hands back starts with a letter saying which kind of flow it belongs to. It is
# visible to anyone and grants nothing: it is used only to pick which page a *failure* returns to,
# for the case where the flow and its cookie have already expired and nothing else is known.
_STATE_KIND = {"SIGN_IN": "s", "ACTIVATE": "a", "LINK": "l"}
LINK_FAILED_PATH = "/profile?google=failed"
# A link that failed because the person can no longer use the app (signed out, session ended,
# removed, coaching suspended, disabled): the Profile page would only bounce them to the sign-in
# page and lose the explanation, so the sign-in page explains it.
LINK_SIGNED_OUT_PATH = "/login?google=link-failed"


@dataclass(frozen=True, slots=True)
class StartedFlow:
    authorization_url: str  # where to send the person
    cookie_value: str  # goes in the pending-flow cookie; only its hash is stored


@dataclass(frozen=True, slots=True)
class Finished:
    """How a callback ends: where to send the browser, and the new session if there is one."""

    path: str
    login: service.LoginResult | None = None


def _failure_path(purpose: str | None) -> str:
    """Where a failed flow of this kind returns to: the page whose advice fits the person."""
    return {"LINK": LINK_FAILED_PATH, "ACTIVATE": ACTIVATION_FAILED_PATH}.get(
        purpose or "", SIGN_IN_FAILED_PATH
    )


def _purpose_from_state(state: str | None) -> str | None:
    """The kind of flow a `state` claims to belong to; only ever used to choose a failure page."""
    kind = (state or "").partition(".")[0]
    return next((purpose for purpose, letter in _STATE_KIND.items() if letter == kind), None)


def failure_for_state(state: str | None) -> Finished:
    """The failure outcome for a callback that cannot be processed at all (Google switched off,
    say), on the page the `state` says the person started from."""
    return Finished(_failure_path(_purpose_from_state(state)))


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
    purpose: str,
    begin: Callable[[Session, dict[str, object]], bool],
    context: TenantContext = NO_CONTEXT,
) -> StartedFlow | None:
    """Make the flow's secrets, let ``begin`` store the flow, and build Google's address.

    ``begin`` returns False when the flow must not start; then nothing is stored.
    """
    cookie_value, nonce, verifier = new_token(), new_token(), new_code_verifier()
    state = f"{_STATE_KIND[purpose]}.{new_token()}"
    flow = {
        "id": new_id(),
        "cookie": hash_token(cookie_value),
        "state": hash_token(state),
        "verifier": verifier,
        "nonce": nonce,
        "origin": origin,
    }
    with database.transaction(context) as session:
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

    started = _start(database, google, origin, "SIGN_IN", begin)
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

    started = _start(database, google, origin, "ACTIVATE", begin)
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
    throttled: bool,
    request_id: str | None,
) -> Finished:
    """Complete a flow Google has called back about. Every failure is one outcome (a redirect to
    the page the flow began on, with ``?google=failed``), so the person cannot learn why. Nothing
    is changed on failure.

    The flow is used up first, in its own transaction: a replay, a wrong ``state`` or a denied
    consent can never be retried. Google is asked only after that. The person's right to do what
    the flow was for is then checked afresh, because minutes may have passed (a removal or
    suspension stops the flow).
    """
    # Used if the flow cannot be found (it may have expired, with its cookie): the `state` still
    # says which page the person started on.
    unknown = failure_for_state(state)
    if not cookie or not state:
        log.info("google_flow_failed", reason="missing_cookie_or_state")
        return unknown
    with database.transaction(NO_CONTEXT) as session:
        flow = session.execute(
            text("SELECT * FROM auth_oauth_take(:cookie, :state)"),
            {"cookie": hash_token(cookie), "state": hash_token(state)},
        ).first()
    if flow is None:
        log.info("google_flow_failed", reason="no_usable_flow")
        return unknown
    failed = Finished(_failure_path(flow.purpose))
    if throttled:
        # Too many callbacks from this address. The flow is used up (it cannot be retried), but the
        # person is still sent to the page the flow began on, and Google is not asked.
        log.info("google_flow_failed", reason="throttled", purpose=flow.purpose)
        return failed
    if not code:
        log.info("google_flow_failed", reason="no_code", purpose=flow.purpose)  # e.g. "Cancel"
        return failed
    try:
        identity = google.identify(
            code=code,
            redirect_uri=redirect_uri(flow.return_origin),
            code_verifier=flow.code_verifier,
            nonce=flow.nonce,
        )
    except GoogleError as exc:
        log.info("google_flow_failed", reason="google_refused", detail=str(exc))
        return failed

    with database.transaction(NO_CONTEXT) as session:
        result: service.LoginResult | None = None
        linked: Literal["linked", "failed", "signed_out"] = "failed"
        if flow.purpose == "SIGN_IN":
            result = _sign_in(session, settings, identity, request_id)
        elif flow.purpose == "ACTIVATE":
            result = _activate(session, settings, flow.id, identity, request_id)
        elif flow.purpose == "LINK":
            linked = _link(session, flow.id, flow.user_id, flow.session_id, identity, request_id)
    if flow.purpose == "LINK":
        log.info("google_link_finished", user_id=str(flow.user_id), outcome=linked)
        if linked == "signed_out":
            return Finished(LINK_SIGNED_OUT_PATH)
        return Finished(LINKED_PATH) if linked == "linked" else failed
    if result is None:
        log.info("google_flow_failed", reason="not_allowed", purpose=flow.purpose)
        return failed
    log.info("google_login_succeeded", user_id=str(result.principal.user_id), purpose=flow.purpose)
    return Finished(SIGNED_IN_PATH, result)


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


def _session_alive(session: Session, user_id: UUID, session_id: UUID) -> bool:
    """Whether this sign-in is still valid (not signed out, revoked or expired)."""
    apply_tenant_context(session, TenantContext(user_id=user_id))
    return bool(
        session.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM sessions s WHERE s.id = :sid AND s.user_id = :uid"
                " AND s.revoked_at IS NULL AND s.idle_expires_at > now()"
                " AND s.absolute_expires_at > now())"
            ),
            {"sid": session_id, "uid": user_id},
        )
    )


def _link(
    session: Session,
    flow_id: UUID,
    user_id: UUID,
    session_id: UUID,
    identity: GoogleIdentity,
    request_id: str | None,
) -> Literal["linked", "failed", "signed_out"]:
    """Link this Google account to the signed-in person who started the flow.

    Checked afresh in this transaction: the person still has access (the check every request
    makes), and the session that started the flow is still theirs and valid (the database function
    locks it). A Google account that belongs to anyone is refused. "signed_out" means the person
    can no longer use the app at all, which changes where the browser should go.
    """
    apply_tenant_context(session, TenantContext(user_id=user_id))
    principal = service.load_principal(session, user_id, session_id)
    if principal is None or not _session_alive(session, user_id, session_id):
        return "signed_out"
    apply_tenant_context(session, principal.tenant_context)
    linked = session.scalar(
        text("SELECT auth_google_link(:flow, :subject, :email)"),
        {"flow": flow_id, "subject": identity.subject, "email": identity.email},
    )
    if linked is None:
        return "failed"
    record_event(
        session,
        action="GOOGLE_LINKED",
        entity_type="user",
        entity_id=user_id,
        organization_id=principal.tenant_context.organization_id,
        actor_user_id=user_id,
        actor_is_platform=principal.is_platform_admin,
        request_id=request_id,
        after={"provider": "google"},
    )
    return "linked"


def start_link(
    database: Database,
    settings: Settings,
    google: GoogleClient,
    principal: Principal,
    return_origin: str,
    password: str,
) -> StartedFlow:
    """Start linking a Google account to the signed-in person, who must give their password now.

    A session alone is never proof: the password comes in this very request. A wrong password
    counts towards the same lockout as signing in, and a locked account is refused like a wrong one.
    """
    origin = _allowed_origin(settings, return_origin)
    wrong_password = False
    with database.transaction(principal.tenant_context) as session:
        methods = session.execute(text("SELECT * FROM auth_my_login_methods()")).one()
        if methods.google_linked:
            raise Conflict(
                "A Google account is already linked. Unlink it first to link another.",
                code="ALREADY_LINKED",
            )
        credential = session.execute(text("SELECT * FROM auth_my_credential()")).first()
        password_ok = verify_password(credential.password_hash if credential else None, password)
        locked = (
            credential is not None
            and credential.locked_until is not None
            and credential.locked_until > datetime.now(UTC)
        )
        if credential is None or locked or not password_ok:
            wrong_password = True
            if credential is not None and not locked:
                session.execute(
                    text("SELECT auth_register_login_failure(:user_id, :max, :lock_for)"),
                    {
                        "user_id": principal.user_id,
                        "max": settings.login_max_failures,
                        "lock_for": timedelta(minutes=settings.login_lock_minutes),
                    },
                )
        else:
            session.execute(
                text("SELECT auth_register_login_success(:user_id)"),
                {"user_id": principal.user_id},
            )
    if wrong_password:  # raised outside the transaction, so the failure count is kept
        log.info("google_link_refused", user_id=str(principal.user_id), reason="password")
        raise PermissionDenied("The password is incorrect.", code="PASSWORD_INCORRECT")

    outcome: list[str] = []

    def begin(session: Session, flow: dict[str, object]) -> bool:
        result = session.scalar(
            text(
                "SELECT auth_oauth_begin_link"
                "(:id, :cookie, :state, :verifier, :nonce, :origin, :session_id)"
            ),
            {**flow, "session_id": principal.session_id},
        )
        outcome.append(str(result))
        return bool(result == "STARTED")

    started = _start(database, google, origin, "LINK", begin, principal.tenant_context)
    if started is None:
        if outcome == ["ALREADY_LINKED"]:
            raise Conflict(
                "A Google account is already linked. Unlink it first to link another.",
                code="ALREADY_LINKED",
            )
        raise Unauthenticated("Please sign in.")  # the session ended meanwhile
    return started


def unlink(database: Database, principal: Principal, request_id: str | None) -> None:
    """Remove the signed-in person's Google account, if they keep a password to sign in with."""
    with database.transaction(principal.tenant_context) as session:
        outcome = session.scalar(text("SELECT auth_google_unlink()"))
        if outcome == "UNLINKED":
            record_event(
                session,
                action="GOOGLE_UNLINKED",
                entity_type="user",
                entity_id=principal.user_id,
                # The person's own account, not the coaching a platform admin may be acting in:
                # that coaching's Owner and admins can read its audit log.
                organization_id=principal.organization_id,
                actor_user_id=principal.user_id,
                actor_is_platform=principal.is_platform_admin,
                request_id=request_id,
                before={"provider": "google"},
            )
    if outcome == "NO_PASSWORD":
        raise Conflict(
            "Google is the only way you sign in. Ask your admin for a password-reset link first.",
            code="NO_OTHER_LOGIN_METHOD",
        )
    if outcome != "UNLINKED":
        raise NotFound("No Google account is linked.", code="GOOGLE_NOT_LINKED")


def login_methods(database: Database, principal: Principal) -> LoginMethods:
    with database.transaction(principal.tenant_context) as session:
        row = session.execute(text("SELECT * FROM auth_my_login_methods()")).one()
    return LoginMethods(
        password=row.has_password,
        google=GoogleStatus(linked=row.google_linked, email=row.google_email),
    )
