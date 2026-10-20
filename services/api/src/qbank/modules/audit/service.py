from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from qbank.modules.audit.models import AuditEvent


def list_events(
    session: Session,
    *,
    organization_id: UUID | None,
    limit: int,
    after: tuple[datetime, UUID] | None,
    entity_type: str | None,
    entity_id: UUID | None,
    actor_user_id: UUID | None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> tuple[list[AuditEvent], bool]:
    """Newest first: one coaching's events, or platform-level ones if ``organization_id`` is None.

    Row-level security already limits what the caller can see; the explicit filter keeps a platform
    admin acting in a coaching from getting platform-level events mixed in. Returns the page and
    whether more rows follow.
    """
    query = select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
    if organization_id is None:
        query = query.where(AuditEvent.organization_id.is_(None))
    else:
        query = query.where(AuditEvent.organization_id == organization_id)
    if after is not None:
        query = query.where(tuple_(AuditEvent.created_at, AuditEvent.id) < after)
    if entity_type is not None:
        query = query.where(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditEvent.entity_id == entity_id)
    if actor_user_id is not None:
        query = query.where(AuditEvent.actor_user_id == actor_user_id)
    if since is not None:
        query = query.where(AuditEvent.created_at >= since)
    if until is not None:
        query = query.where(AuditEvent.created_at < until)
    rows = list(session.scalars(query.limit(limit + 1)))
    return rows[:limit], len(rows) > limit
