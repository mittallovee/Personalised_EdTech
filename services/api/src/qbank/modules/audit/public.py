"""Public interface of the audit module: append an audit event inside the caller's transaction."""

from typing import Any
from uuid import UUID

import structlog
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
