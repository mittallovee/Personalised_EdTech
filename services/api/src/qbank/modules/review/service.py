from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import PermissionDenied
from qbank.core.permissions import may_see_review_queue
from qbank.modules.questions.public import (
    QueueCounts,
    QueueFilters,
    QueueRow,
    State,
    list_queue,
    queue_counts,
)


def _require_queue_access(principal: Principal) -> None:
    """Holders of at least one review grant, and admins. Everyone else is refused; the grant comes
    from the database on every request, never from the client."""
    if not may_see_review_queue(principal):
        raise PermissionDenied("You don't have permission to do this.")


def queue(
    session: Session,
    principal: Principal,
    *,
    state: State | None,
    subject_id: UUID | None,
    chapter_id: UUID | None,
    author_id: UUID | None,
    language: str | None,
    older_than_days: int | None,
    limit: int,
    after: tuple[datetime, UUID] | None,
) -> tuple[list[QueueRow], bool]:
    _require_queue_access(principal)
    filters = QueueFilters(
        state=state,
        subject_id=subject_id,
        chapter_id=chapter_id,
        author_id=author_id,
        language=language,
        older_than_days=older_than_days,
    )
    return list_queue(session, principal, filters, limit=limit, after=after)


def counts(session: Session, principal: Principal) -> QueueCounts:
    _require_queue_access(principal)
    return queue_counts(session, principal)
