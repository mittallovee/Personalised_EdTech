"""Looking up passage checkpoints by id (shared by the question and passage services)."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.modules.questions.models import PassageRevision


def checkpoint_ids(session: Session, ids: Collection[UUID]) -> set[UUID]:
    """Which of these ids are checkpoints (frozen passage revisions) of the session's coaching.

    Row-level security hides every other coaching's revisions, and a working revision is not a
    checkpoint, so both look exactly like an id that does not exist.
    """
    if not ids:
        return set()
    return set(
        session.scalars(
            select(PassageRevision.id).where(
                PassageRevision.id.in_(ids), PassageRevision.frozen_at.is_not(None)
            )
        )
    )
