from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.orm import Session

from qbank.core.errors import NotFound
from qbank.modules.notifications.models import Notification


def list_notifications(
    session: Session,
    *,
    user_id: UUID,
    organization_id: UUID,
    unread_only: bool,
    limit: int,
    after: tuple[datetime, UUID] | None,
) -> tuple[list[Notification], bool]:
    """The person's own notifications in this coaching, newest first, and whether more follow.

    Row-level security already limits the rows to the person; the explicit filters say so in the
    code too."""
    query = (
        select(Notification)
        .where(Notification.user_id == user_id, Notification.organization_id == organization_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    if after is not None:
        query = query.where(tuple_(Notification.created_at, Notification.id) < after)
    rows = list(session.scalars(query.limit(limit + 1)))
    return rows[:limit], len(rows) > limit


def unread_count(session: Session, *, user_id: UUID, organization_id: UUID) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )


def mark_read(
    session: Session, *, user_id: UUID, organization_id: UUID, notification_id: UUID
) -> Notification:
    """Mark one of the person's own notifications as read (again is fine: the first time stays).
    Someone else's, or one that does not exist, is not found."""
    found = session.scalar(
        select(Notification)
        .where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
        )
        .with_for_update()
    )
    if found is None:
        raise NotFound("That notification was not found.")
    if found.read_at is None:
        found.read_at = func.now()
        session.flush()
        session.refresh(found)
    return found


def mark_all_read(session: Session, *, user_id: UUID, organization_id: UUID) -> int:
    result = session.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.organization_id == organization_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=func.now())
    )
    return int(getattr(result, "rowcount", 0) or 0)
