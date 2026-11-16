from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from qbank.core.pagination import PageInfo


class QueueState(StrEnum):
    """The views of the queue. Nothing else is a queue state: drafts and published questions are
    not waiting for anyone."""

    IN_REVIEW = "IN_REVIEW"
    QC_PASSED = "QC_PASSED"
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class QueueItem(BaseModel):
    question_id: UUID
    code: str
    question_type: str | None
    language: str | None
    subject_id: UUID | None = Field(description="Look the name up in the coaching's syllabus.")
    chapter_id: UUID | None
    state: QueueState
    version_number: int = Field(description="2 or more for a correction of a published question.")
    submitted_by: UUID = Field(description="Whoever sent this version in for review.")
    waiting_since: datetime = Field(description="When it entered its present state.")


class QueuePage(BaseModel):
    data: list[QueueItem]
    page: PageInfo


class QueueCounts(BaseModel):
    waiting_for_qc: int = Field(ge=0, description="In review, waiting for QC.")
    waiting_for_approval: int = Field(ge=0, description="Passed QC, waiting for approval.")
    waiting_to_publish: int = Field(ge=0, description="Approved, waiting to be published.")
    returned_to_me: int = Field(
        ge=0, description="Questions you sent in that came back with reasons."
    )
