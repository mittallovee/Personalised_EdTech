"""Public interface of the identity module. Other modules import only from here."""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from qbank.core.errors import Conflict
from qbank.core.ids import new_id
from qbank.core.security import hash_token, new_token
from qbank.modules.identity.models import INVITED, AccountLink, User, UserSession
from qbank.modules.organizations.public import lock_membership

__all__ = [
    "ACTIVATION_LINK_LIFETIME",
    "INVITED",
    "RESET_LINK_LIFETIME",
    "IssuedLink",
    "LinkPurpose",
    "create_invited_user",
    "display_names",
    "issue_account_link",
    "reserve_email",
    "set_acting_organization",
    "user_status",
]


def display_names(session: Session, user_ids: Collection[UUID]) -> dict[UUID, str]:
    """Names of the given users that the current tenant context may see (others are left out)."""
    if not user_ids:
        return {}
    rows = session.execute(select(User.id, User.display_name).where(User.id.in_(user_ids)))
    return {row.id: row.display_name for row in rows}


# --- Invitations and one-time account links (ADR-0015) --------------------------------------------

ACTIVATION_LINK_LIFETIME = timedelta(hours=24)  # B-05
RESET_LINK_LIFETIME = timedelta(hours=1)  # M2 design note, owner decision 20 Oct 2026


class LinkPurpose(StrEnum):
    ACTIVATION = "ACTIVATION"
    RESET = "RESET"


@dataclass(frozen=True, slots=True)
class IssuedLink:
    """A new link. ``token`` is shown once to the person who asked for it and never stored."""

    token: str
    expires_at: datetime


def create_invited_user(session: Session, display_name: str) -> UUID:
    """A new account that cannot sign in until it is activated with a link."""
    user_id = new_id()
    session.add(User(id=user_id, display_name=display_name, status=INVITED))
    session.flush()
    return user_id


def reserve_email(session: Session, user_id: UUID, email: str) -> None:
    """Give ``email`` to a new invited account, or fail with ``409 EMAIL_TAKEN`` (B-07).

    The account must already be an active member of the current coaching (write the membership
    first). The reservation is part of the caller's transaction.
    """
    reserved = session.scalar(
        text("SELECT auth_reserve_email(:email, :user_id)"), {"email": email, "user_id": user_id}
    )
    if not reserved:
        raise Conflict("An account with this email already exists.", code="EMAIL_TAKEN")


def issue_account_link(
    session: Session,
    *,
    organization_id: UUID,
    membership_id: UUID,
    user_id: UUID,
    purpose: LinkPurpose,
    created_by: UUID,
) -> IssuedLink:
    """A new link for a member of the current coaching; an earlier unused one stops working."""
    # Requests for the same member take turns: otherwise two at once could each revoke the old
    # link and insert their own. A unique index also allows only one usable link per purpose.
    lock_membership(session, membership_id)
    now = datetime.now(UTC)
    session.execute(
        update(AccountLink)
        .where(
            AccountLink.user_id == user_id,
            AccountLink.purpose == purpose,
            AccountLink.used_at.is_(None),
            AccountLink.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    token = new_token()
    lifetime = (
        ACTIVATION_LINK_LIFETIME if purpose is LinkPurpose.ACTIVATION else RESET_LINK_LIFETIME
    )
    expires_at = now + lifetime
    # Plain INSERT (no RETURNING): the runtime role may write the token hash but never read it.
    session.execute(
        text(
            "INSERT INTO account_links"
            " (id, organization_id, membership_id, user_id, purpose, token_hash, created_by,"
            " expires_at)"
            " VALUES (:id, :organization_id, :membership_id, :user_id, :purpose, :token_hash,"
            " :created_by, :expires_at)"
        ),
        {
            "id": new_id(),
            "organization_id": organization_id,
            "membership_id": membership_id,
            "user_id": user_id,
            "purpose": purpose.value,
            "token_hash": hash_token(token),
            "created_by": created_by,
            "expires_at": expires_at,
        },
    )
    return IssuedLink(token=token, expires_at=expires_at)


def user_status(session: Session, user_id: UUID) -> str | None:
    """INVITED, ACTIVE or DISABLED; None if the account is not visible here."""
    return session.scalar(select(User.status).where(User.id == user_id))


def set_acting_organization(
    session: Session, session_id: UUID, organization_id: UUID | None
) -> None:
    """Record which coaching a platform admin's sign-in session acts in (None: none). A-06.

    Only the session's own user can change it (row-level security on sessions).
    """
    session.execute(
        update(UserSession)
        .where(UserSession.id == session_id)
        .values(acting_organization_id=organization_id)
    )
