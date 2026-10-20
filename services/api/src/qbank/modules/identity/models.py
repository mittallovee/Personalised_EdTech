from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from qbank.core.db import Base
from qbank.core.ids import new_id

INVITED = "INVITED"  # created by an invitation, not activated yet: cannot sign in


class User(Base):
    """A person. Not owned by a coaching: membership links a user to one coaching (B-07)."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PasswordCredential(Base):
    """Email + password login method. Not readable by the runtime role (see migration 0002)."""

    __tablename__ = "password_credentials"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    email: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str]
    failed_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PlatformRole(Base):
    __tablename__ = "platform_roles"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(40), primary_key=True)


class UserSession(Base):
    """A signed-in browser session. Only hashes of the cookie and CSRF tokens are stored."""

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str]
    csrf_token_hash: Mapped[str]
    acting_organization_id: Mapped[UUID | None] = mapped_column(ForeignKey("organizations.id"))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AccountLink(Base):
    """A one-time activation or reset link (ADR-0015). The token itself is never stored.

    ``token_hash`` is write-only for the runtime role (no SELECT privilege), so it is not mapped
    here; links are inserted with plain SQL in ``public.issue_account_link``.
    """

    __tablename__ = "account_links"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_id)
    organization_id: Mapped[UUID]
    membership_id: Mapped[UUID]  # with user_id: must be a member of this coaching (composite key)
    user_id: Mapped[UUID]
    purpose: Mapped[str] = mapped_column(String(20))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
