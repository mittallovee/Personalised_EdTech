"""Public interface of the notifications module: send one inside the caller's transaction."""

from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from qbank.modules.notifications.models import Notification

log = structlog.get_logger("qbank.notifications")


def notify(
    session: Session,
    *,
    organization_id: UUID,
    user_id: UUID,
    kind: str,
    data: dict[str, Any],
) -> None:
    """Add a notification to the caller's transaction, so it commits or rolls back with the step
    that caused it. ``data`` holds ids and short facts for the screen to word; it is shown as text,
    never as markup."""
    session.add(
        Notification(organization_id=organization_id, user_id=user_id, kind=kind, data=data)
    )
    session.flush()
    log.info(
        "notification_sent",
        kind=kind,
        organization_id=str(organization_id),
        user_id=str(user_id),
    )
