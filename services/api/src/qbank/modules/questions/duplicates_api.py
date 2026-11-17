"""The duplicate check of one question, and the decisions about it (D-16)."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.modules.questions import duplicates
from qbank.modules.questions.models import DuplicateDecision

router = APIRouter(prefix="/api/v1/questions", tags=["questions"])

DecisionKind = Literal["NOT_DUPLICATE", "DUPLICATE_OF"]


class DecisionOut(BaseModel):
    other_question_id: UUID
    decision: DecisionKind
    note: str
    decided_by: UUID
    decided_at: datetime


class DecideDuplicate(BaseModel):
    other_question_id: UUID
    decision: DecisionKind = Field(
        description="`DUPLICATE_OF`: this question copies the other one (archive this one; nothing"
        " is merged). `NOT_DUPLICATE`: they only look alike."
    )
    note: str = Field(min_length=1, max_length=1000, description="Why, in a few words.")


class Blocker(BaseModel):
    question_id: UUID
    code: str


class DuplicateOut(BaseModel):
    question_id: UUID
    code: str
    state: str = Field(description="The workflow state of the version the bank shows.")
    match: Literal["EXACT", "NEAR"] = Field(
        description="`EXACT`: the same format, stem, options and answer (case and spacing of the"
        " prose aside; equations as written). `NEAR`: very similar text."
    )
    similarity_percent: int = Field(ge=0, le=100, description="How alike the two texts are.")
    preview: str = Field(description="The beginning of the other question's stem (plain text).")
    decision: DecisionOut | None = Field(
        description="The newest decision about this pair, for the text as it is now."
    )


class DuplicatesOut(BaseModel):
    checked_revision_id: UUID = Field(
        description="The text that was checked: the one under review or published, else the"
        " working copy of a draft."
    )
    version_number: int
    data: list[DuplicateOut] = Field(
        description="Exact matches first, then near ones, closest first."
    )
    qc_blocked_by: list[Blocker] = Field(
        description="What stops Pass QC now: exact matches in the shared bank with no"
        " `NOT_DUPLICATE` decision, and questions this one was marked a duplicate of."
    )


def _decision(row: DuplicateDecision | None) -> DecisionOut | None:
    if row is None:
        return None
    return DecisionOut(
        other_question_id=row.other_master_id,
        decision="DUPLICATE_OF" if row.decision == "DUPLICATE_OF" else "NOT_DUPLICATE",
        note=row.note,
        decided_by=row.actor_id,
        decided_at=row.created_at,
    )


@router.get(
    "/{question_id}/duplicates",
    summary="Possible duplicates of a question (D-16)",
    description="Questions of this coaching with the same content (`EXACT`) or very similar text"
    " (`NEAR`), at most 20 of each, never archived ones, never another coaching's, and only ones"
    " you may open, with the newest decision about each. A person decides whether they are"
    " duplicates; nothing is merged or changed.",
    responses={
        404: {"description": "No such question that you may open (`NOT_FOUND`)"},
        503: {"description": "The check took too long and was stopped (`SEARCH_TIMED_OUT`)"},
    },
)
def get_duplicates(
    question_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> DuplicatesOut:
    timeout_ms: int = request.app.state.settings.search_timeout_ms
    with database.transaction(principal.tenant_context) as session:
        check = duplicates.check_duplicates(session, principal, question_id, timeout_ms=timeout_ms)
        return DuplicatesOut(
            checked_revision_id=check.revision.id,
            version_number=check.version.number,
            data=[
                DuplicateOut(
                    question_id=candidate.master_id,
                    code=candidate.code,
                    state=candidate.state,
                    match="EXACT" if candidate.exact else "NEAR",
                    similarity_percent=candidate.similarity_percent,
                    preview=candidate.preview,
                    decision=_decision(check.decisions.get(candidate.master_id)),
                )
                for candidate in check.candidates
            ],
            qc_blocked_by=[Blocker(question_id=q, code=c) for q, c in check.blockers],
        )


@router.post(
    "/{question_id}/duplicates/decisions",
    status_code=status.HTTP_201_CREATED,
    summary="Record whether a question is a duplicate of another (D-16)",
    description="For the text as it is now: an edit that changes the question needs a new"
    " decision, and a newer decision replaces an older one (both are kept). The author, admins,"
    " edit-others holders and quality control may decide. An exact match with no `NOT_DUPLICATE`"
    " decision, or a `DUPLICATE_OF`, blocks Pass QC (`QC_BLOCKED_DUPLICATE`). Nothing is merged"
    " or deleted.",
    responses={
        403: {"description": "You may not decide this (`PERMISSION_DENIED`)"},
        404: {"description": "No such question, or other question, that you may open"},
        409: {"description": "The question is published (`DUPLICATE_DECISION_CLOSED`)"},
        422: {"description": "The same question, an empty question, or no note"},
    },
)
def decide_duplicate(
    question_id: UUID,
    body: DecideDuplicate,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> DecisionOut:
    with database.transaction(principal.tenant_context) as session:
        row = duplicates.decide(
            session,
            principal,
            question_id,
            other_question_id=body.other_question_id,
            decision=body.decision,
            note=body.note,
            request_id=request.state.request_id,
        )
        result = _decision(row)
    if result is None:  # decide always returns a row; this only satisfies the type checker
        raise RuntimeError("No decision was recorded.")
    return result
