"""Sign-in, sign-out, session checks and platform-admin bootstrap (B-01, B-11, A-03)."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.config import Settings
from qbank.core.db import Database
from qbank.core.errors import Conflict, Unauthenticated
from qbank.core.ids import new_id
from qbank.core.security import hash_password, hash_token, new_token, verify_password
from qbank.core.tenancy import NO_CONTEXT, TenantContext, apply_tenant_context
from qbank.modules.audit.public import record_event
from qbank.modules.identity.models import PasswordCredential, PlatformRole, User, UserSession
from qbank.modules.organizations.public import find_active_membership, get_organization

log = structlog.get_logger("qbank.identity")

PLATFORM_ADMIN = "PLATFORM_ADMIN"
# One message for every login failure, so callers cannot learn whether an account exists.
LOGIN_FAILED = "Email or password is incorrect."
# Refresh the idle expiry at most this often, to avoid a database write on every request.
# Never more than a tenth of the idle window, so a short window is still extended in time.
_SEEN_REFRESH_MAX = timedelta(minutes=5)


@dataclass(frozen=True, slots=True)
class LoginResult:
    principal: Principal
    session_token: str  # goes into the HttpOnly cookie; never stored in plain form
    csrf_token: str  # readable by the web app; sent back in X-CSRF-Token on changes
    expires_at: datetime


def _now() -> datetime:
    return datetime.now(UTC)


def _load_principal(session: Session, user_id: UUID, session_id: UUID | None) -> Principal | None:
    """Build the principal for an active user, or None if they may not use the app.

    Runs inside a transaction whose context already identifies ``user_id``.
    """
    user = session.get(User, user_id)
    if user is None or user.status != "ACTIVE":
        return None
    is_platform_admin = (
        session.scalar(
            select(PlatformRole.role).where(
                PlatformRole.user_id == user_id, PlatformRole.role == PLATFORM_ADMIN
            )
        )
        is not None
    )
    membership = find_active_membership(session, user_id)
    if membership is not None:
        apply_tenant_context(
            session, TenantContext(organization_id=membership.organization_id, user_id=user_id)
        )
        organization = get_organization(session, membership.organization_id)
        if organization is None or organization.status != "ACTIVE":
            membership = None  # suspended coaching (A-07): no access through it
    if membership is None and not is_platform_admin:
        return None
    return Principal(
        user_id=user.id,
        display_name=user.display_name,
        is_platform_admin=is_platform_admin,
        organization_id=membership.organization_id if membership else None,
        role=membership.role if membership else None,
        session_id=session_id,
    )


def login(
    database: Database, settings: Settings, email: str, password: str, request_id: str | None
) -> LoginResult:
    """Check the password and start a session. Every failure raises the same ``Unauthenticated``.

    A failed attempt is committed before the error is raised: raising inside the transaction would
    roll back the failure counter and the lockout would never trigger.
    """
    failure: str | None = None
    result: LoginResult | None = None
    with database.transaction(NO_CONTEXT) as session:
        found = session.execute(
            text("SELECT * FROM auth_find_login(:email)"), {"email": email.strip().lower()}
        ).first()
        password_ok = verify_password(found.password_hash if found else None, password)
        locked = (
            found is not None and found.locked_until is not None and found.locked_until > _now()
        )

        if found is None:
            failure = "unknown_email"
        elif locked:
            failure = "locked"
        elif not password_ok:
            failure = "bad_password"
            session.execute(
                text("SELECT auth_register_login_failure(:user_id, :max, :lock_for)"),
                {
                    "user_id": found.user_id,
                    "max": settings.login_max_failures,
                    "lock_for": timedelta(minutes=settings.login_lock_minutes),
                },
            )
        else:
            result = _start_session(session, settings, found.user_id, request_id)
            if result is None:
                failure = "no_active_access"

    if result is None:
        log.info("login_failed", reason=failure, user_id=str(found.user_id) if found else None)
        raise Unauthenticated(LOGIN_FAILED)
    log.info("login_succeeded", user_id=str(result.principal.user_id))
    return result


def _start_session(
    session: Session, settings: Settings, user_id: UUID, request_id: str | None
) -> LoginResult | None:
    apply_tenant_context(session, TenantContext(user_id=user_id))
    principal = _load_principal(session, user_id, session_id=None)
    if principal is None:
        return None
    session.execute(text("SELECT auth_register_login_success(:user_id)"), {"user_id": user_id})

    apply_tenant_context(session, principal.tenant_context)
    now = _now()
    session_token, csrf_token = new_token(), new_token()
    expires_at = now + timedelta(days=settings.session_absolute_days)
    user_session = UserSession(
        id=new_id(),
        user_id=user_id,
        token_hash=hash_token(session_token),
        csrf_token_hash=hash_token(csrf_token),
        last_seen_at=now,
        idle_expires_at=min(now + timedelta(minutes=settings.session_idle_minutes), expires_at),
        absolute_expires_at=expires_at,
    )
    session.add(user_session)
    record_event(
        session,
        action="USER_SIGNED_IN",
        entity_type="user",
        entity_id=user_id,
        organization_id=principal.organization_id,
        actor_user_id=user_id,
        actor_is_platform=principal.is_platform_admin,
        request_id=request_id,
    )
    return LoginResult(
        replace(principal, session_id=user_session.id), session_token, csrf_token, expires_at
    )


@dataclass(frozen=True, slots=True)
class SessionCheck:
    principal: Principal
    csrf_token_hash: str


def resolve_session(database: Database, settings: Settings, token: str) -> SessionCheck | None:
    """Return the signed-in principal for a session cookie, or None if it is not valid now."""
    with database.transaction(NO_CONTEXT) as session:
        row = session.execute(
            text("SELECT * FROM auth_find_session(:token_hash)"), {"token_hash": hash_token(token)}
        ).first()
        now = _now()
        if (
            row is None
            or row.revoked_at is not None
            or row.idle_expires_at <= now
            or row.absolute_expires_at <= now
        ):
            return None

        apply_tenant_context(session, TenantContext(user_id=row.user_id))
        principal = _load_principal(session, row.user_id, session_id=row.id)
        if principal is None:
            return None  # user disabled or removed from their coaching since signing in

        idle_window = timedelta(minutes=settings.session_idle_minutes)
        if now - row.last_seen_at > min(_SEEN_REFRESH_MAX, idle_window / 10):
            apply_tenant_context(session, TenantContext(user_id=row.user_id))
            session.execute(
                update(UserSession)
                .where(UserSession.id == row.id)
                .values(
                    last_seen_at=now,
                    idle_expires_at=min(now + idle_window, row.absolute_expires_at),
                )
            )
        return SessionCheck(principal, row.csrf_token_hash)


def logout(database: Database, principal: Principal, request_id: str | None) -> None:
    with database.transaction(principal.tenant_context) as session:
        session.execute(
            update(UserSession)
            .where(UserSession.id == principal.session_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=_now())
        )
        record_event(
            session,
            action="USER_SIGNED_OUT",
            entity_type="user",
            entity_id=principal.user_id,
            organization_id=principal.organization_id,
            actor_user_id=principal.user_id,
            actor_is_platform=principal.is_platform_admin,
            request_id=request_id,
        )


def create_platform_admin(owner_database: Database, email: str, name: str, password: str) -> UUID:
    """Create the first (or another) platform admin (A-03). Run by the operator as table owner."""
    normalized = email.strip().lower()
    with owner_database.transaction(TenantContext(is_platform=True)) as session:
        taken = session.scalar(
            select(PasswordCredential.user_id).where(PasswordCredential.email == normalized)
        )
        if taken is not None:
            raise Conflict("An account with this email already exists.", code="EMAIL_TAKEN")
        user = User(id=new_id(), display_name=name)
        session.add(user)
        session.flush()
        session.add(
            PasswordCredential(
                user_id=user.id, email=normalized, password_hash=hash_password(password)
            )
        )
        session.add(PlatformRole(user_id=user.id, role=PLATFORM_ADMIN))
        record_event(
            session,
            action="PLATFORM_ADMIN_CREATED",
            entity_type="user",
            entity_id=user.id,
            organization_id=None,
            actor_user_id=None,
            actor_is_platform=True,
            after={"email": normalized, "display_name": name},
        )
    return user.id
