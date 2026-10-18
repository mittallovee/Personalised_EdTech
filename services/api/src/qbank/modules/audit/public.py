"""Public interface of the audit module: append an audit event inside the caller's transaction."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from qbank.modules.audit.models import AuditEvent


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
