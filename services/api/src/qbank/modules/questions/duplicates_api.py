"""The duplicate check of one question (D-16)."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.modules.questions import duplicates

router = APIRouter(prefix="/api/v1/questions", tags=["questions"])


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


class DuplicatesOut(BaseModel):
    checked_revision_id: UUID = Field(
        description="The text that was checked: the one under review or published, else the"
        " working copy of a draft."
    )
    version_number: int
    data: list[DuplicateOut] = Field(
        description="Exact matches first, then near ones, closest first."
    )


@router.get(
    "/{question_id}/duplicates",
    summary="Possible duplicates of a question (D-16)",
    description="Questions of this coaching with the same content (`EXACT`) or very similar text"
    " (`NEAR`), at most 20 of each, never archived ones, never another coaching's, and only ones"
    " you may open. A person decides whether they are duplicates; nothing is merged or changed.",
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
                )
                for candidate in check.candidates
            ],
        )
