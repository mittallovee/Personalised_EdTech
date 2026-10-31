"""What the question routes send and receive (API style guide)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from qbank.core.pagination import PageInfo
from qbank.modules.questions.findings import Level


class CreateQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: dict[str, Any] = Field(
        description="The question's content (schema version 1). It may be incomplete: a draft"
        " with gaps is saved and the response lists what is missing.",
    )


class SaveQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: dict[str, Any] = Field(
        description="The whole content, replacing the working revision's. Gaps are fine."
    )


class FindingOut(BaseModel):
    path: str = Field(
        description="Which field, like `options[2].content[0].text`.", examples=["answer"]
    )
    code: str = Field(description="Stable code to branch on, never the message.")
    level: Level
    message: str = Field(description="Plain words for the author; the wording may change.")


class FindingCounts(BaseModel):
    error: int
    incomplete: int
    warning: int


class QuestionOut(BaseModel):
    id: UUID
    code: str = Field(description="The permanent 8-character code, never reused.")
    version_number: int
    revision: int = Field(description="Also the ETag of the working revision.")
    archived: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    content: dict[str, Any]
    findings: list[FindingOut] = Field(
        description="Computed from the content on every read, never stored."
    )


class QuestionSummary(BaseModel):
    id: UUID
    code: str
    question_type: str | None = Field(description="From the content; null while not chosen.")
    archived: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    finding_counts: FindingCounts


class QuestionPage(BaseModel):
    data: list[QuestionSummary]
    page: PageInfo


class RevisionSummary(BaseModel):
    number: int = Field(description="Counts up within the version.")
    working: bool = Field(description="The one being edited; the others are frozen checkpoints.")
    version_number: int
    author_id: UUID = Field(description="Who saved it last.")
    content_hash: str | None = Field(description="SHA-256 of the content; set when frozen.")
    frozen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RevisionList(BaseModel):
    data: list[RevisionSummary]


class RevisionOut(RevisionSummary):
    content: dict[str, Any]
    findings: list[FindingOut] = Field(description="Computed as of now, with today's rules.")
