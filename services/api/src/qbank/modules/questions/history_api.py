"""Routes for a question's history and for comparing two of its texts (E-08, E-09)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.modules.questions import history
from qbank.modules.questions.history_schemas import (
    ChangeOut,
    DiffOut,
    DiffRevision,
    HistoryEntry,
    HistoryOut,
    SegmentOut,
)

router = APIRouter(prefix="/api/v1/questions", tags=["questions"])

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "No such question, or no such text of it, that you may read. A question or"
        " correction that is still someone else's draft is also 404 (`NOT_FOUND`)"
    }
}


def _side(ref: history.RevisionRef) -> DiffRevision:
    return DiffRevision(
        id=ref.id, version_number=ref.version_number, number=ref.number, frozen_at=ref.frozen_at
    )


@router.get(
    "/{question_id}/history",
    summary="Who did what to a question, oldest first (E-09)",
    description="The start of the question, each saved checkpoint, every review step (a return"
    " with its reasons and note), the start of a correction, and archive and restore. Only the"
    " versions you may read are included: the steps of a correction that is still a private draft"
    " are not listed to someone who may read only the published version.",
    responses=_NOT_FOUND,
)
def get_history(
    question_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> HistoryOut:
    with database.transaction(principal.tenant_context) as session:
        items = history.question_history(session, principal, question_id)
        return HistoryOut(
            data=[
                HistoryEntry(
                    kind=item.kind,
                    at=item.at,
                    actor_id=item.actor_id,
                    version_number=item.version_number,
                    revision_id=item.revision_id,
                    reasons=list(item.reasons),
                    note=item.note,
                )
                for item in items
            ]
        )


@router.get(
    "/{question_id}/diff",
    summary="What changed between two saved texts of a question (E-08)",
    description="`from` and `to` are revision ids (from the history or the revision list); both"
    " must belong to this question, and each is checked on its own against what you may read."
    " Changed prose comes with word-level segments; an equation or picture counts as one item.",
    responses=_NOT_FOUND,
)
def get_diff(
    question_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    from_revision: Annotated[UUID, Query(alias="from", description="The older text.")],
    to_revision: Annotated[UUID, Query(alias="to", description="The newer text.")],
) -> DiffOut:
    with database.transaction(principal.tenant_context) as session:
        result = history.diff_revisions(session, principal, question_id, from_revision, to_revision)
        return DiffOut(
            from_revision=_side(result.before),
            to_revision=_side(result.after),
            identical=not result.changes,
            changes=[
                ChangeOut(
                    op=change.op,
                    path=list(change.path),
                    before=change.before,
                    after=change.after,
                    segments=(
                        [SegmentOut(kind=s.kind, text=s.text) for s in change.segments]
                        if change.segments is not None
                        else None
                    ),
                )
                for change in result.changes
            ],
        )
