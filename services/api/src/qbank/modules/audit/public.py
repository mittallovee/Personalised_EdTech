"""Public interface of the audit module: append an audit event inside the caller's transaction, and
read back who did which of a few named things to one entity."""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.modules.audit.models import AuditEvent

log = structlog.get_logger("qbank.audit")


def record_event(
    session: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    organization_id: UUID | None,
    actor_user_id: UUID | None,
    actor_is_platform: bool = False,
    request_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditEvent(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_is_platform=actor_is_platform,
            request_id=request_id,
            before=before,
            after=after,
        )
    )
    # Names and IDs only: the before/after data can hold coaching content and stays in the table.
    # Written when recorded; the audit row itself commits or rolls back with the caller.
    log.info(
        "audit_recorded",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        **({"organization_id": str(organization_id)} if organization_id else {}),
        actor_user_id=str(actor_user_id) if actor_user_id else None,
        actor_is_platform=actor_is_platform,
    )


@dataclass(frozen=True, slots=True)
class EntityAction:
    """Who did one thing to an entity, and when, with the event's ``after`` data (names and ids;
    the caller asks only for kinds of event whose data it knows to be safe to use)."""

    id: UUID
    action: str
    actor_user_id: UUID | None
    at: datetime
    after: dict[str, Any] | None


def entity_actions(
    session: Session,
    *,
    organization_id: UUID,
    entity_type: str,
    entity_id: UUID,
    actions: Collection[str],
) -> list[EntityAction]:
    """The given kinds of event recorded for one entity of one coaching, oldest first. Whether the
    caller may see them is the caller's decision: this is a plain read, not a page of the log."""
    rows = session.execute(
        select(
            AuditEvent.id,
            AuditEvent.action,
            AuditEvent.actor_user_id,
            AuditEvent.created_at,
            AuditEvent.after,
        )
        .where(
            AuditEvent.organization_id == organization_id,
            AuditEvent.entity_type == entity_type,
            AuditEvent.entity_id == entity_id,
            AuditEvent.action.in_(list(actions)),
        )
        .order_by(AuditEvent.created_at, AuditEvent.id)
    ).all()
    return [
        EntityAction(row.id, row.action, row.actor_user_id, row.created_at, row.after)
        for row in rows
    ]
