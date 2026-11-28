from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from qbank.core.pagination import PageInfo

Kind = Literal["PDF", "DOCX", "JPEG", "PNG", "WEBP", "HEIC"]
State = Literal[
    "UPLOADED", "RENDERING", "READY", "EXTRACTING", "DONE", "PARTIAL", "FAILED", "CANCELLED"
]


class IngestFileOut(BaseModel):
    id: UUID
    file_name: str = Field(description="A label only: what the file was called when it was sent.")
    kind: Kind = Field(description="Decided from the file's first bytes, never from its name.")
    byte_size: int
    state: State = Field(
        description="`UPLOADED` waiting to be read, `RENDERING` being turned into pages, `READY`"
        " pages made, `EXTRACTING` questions being read, then `DONE`, `PARTIAL` (some pages"
        " failed), `FAILED` or `CANCELLED`. A client must treat a state it does not know as in"
        " progress."
    )
    page_count: int | None
    error_code: str | None = Field(description="Why a file `FAILED`, as a code; null otherwise.")
    uploaded_by: UUID
    duplicate_of: UUID | None = Field(
        default=None,
        description="Only on upload: an earlier file of this coaching with exactly the same bytes."
        " The new upload is kept anyway.",
    )
    created_at: datetime
    updated_at: datetime


class IngestFilePage(BaseModel):
    data: list[IngestFileOut]
    page: PageInfo


class IngestPageOut(BaseModel):
    page_no: int
    state: Literal["READY", "FAILED"]
    width: int | None
    height: int | None
    has_picture: bool = Field(description="False for a page of a Word file: it has text only.")
    text_chars: int = Field(description="How much text the document itself carries on this page.")
    text: str | None = Field(description="That text, as text (never markup).")
    figures: int = Field(description="Pictures found inside a Word page.")
    warnings: list[str] = Field(description="For example `EQUATION_AS_TEXT`: check it by eye.")
    error_code: str | None


class IngestPagesOut(BaseModel):
    data: list[IngestPageOut]


class StartedRun(BaseModel):
    id: UUID
    file_id: UUID
    state: Literal["RUNNING", "DONE", "PARTIAL", "FAILED", "CANCELLED"]
    pages_total: int
    pages_done: int
    pages_failed: int
    prompt_version: str = Field(description="Which built-in wording read the pages.")
    error_code: str | None
    started_at: datetime
    finished_at: datetime | None


class IngestRunsOut(BaseModel):
    data: list[StartedRun]


class CandidateOut(BaseModel):
    id: UUID
    file_id: UUID
    run_id: UUID
    page_no: int
    ordinal: int
    region: dict[str, float] | None = Field(
        description="The question's box on the page as fractions of its width and height."
    )
    content: dict[str, Any] = Field(
        description="What a person edits: the question as the editor stores it."
    )
    raw: dict[str, Any] = Field(description="What the model read, exactly; never changed.")
    findings: list[dict[str, str]] = Field(
        description="What the question checks say is wrong or missing (path, code, level, message)."
    )
    confidence: Literal["HIGH", "MEDIUM", "LOW"]
    warnings: list[str] = Field(
        description="`HANDWRITTEN`, `LOW_CONFIDENCE`, `ANSWER_NOT_READ`, `OVERPRECISE_ANSWER`."
    )
    state: Literal["NEW", "ACCEPTED", "REJECTED", "DUPLICATE"]
    question_id: UUID | None = Field(description="The question made, or the one it is the same as.")
    reject_reason: str | None
    revision: int = Field(description="Send as the ETag to change the content.")


class CandidatesOut(BaseModel):
    data: list[CandidateOut]


class EditCandidate(BaseModel):
    content: dict[str, Any]


class RejectCandidate(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class SameAs(BaseModel):
    question_id: UUID


class CandidateDuplicateOut(BaseModel):
    question_id: UUID
    code: str
    exact: bool
    similarity_percent: int
    preview: str


class CandidateDuplicatesOut(BaseModel):
    data: list[CandidateDuplicateOut]


class IngestSettingsOut(BaseModel):
    model_id: UUID | None = Field(description="The model pages are read with; null until chosen.")
    revision: int = Field(description="0 until first saved. Send it as the ETag.")


class SaveIngestSettings(BaseModel):
    model_config = {"extra": "forbid"}

    model_id: UUID | None


class GoldenSetIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class GoldenSetOut(BaseModel):
    id: UUID
    name: str
    cases: int = Field(description="How many questions are in the key.")
    created_at: datetime


class GoldenSetsOut(BaseModel):
    data: list[GoldenSetOut]


class GoldenCaseIn(BaseModel):
    candidate_id: UUID = Field(description="A candidate that was accepted.")


class GoldenCaseOut(BaseModel):
    id: UUID
    set_id: UUID
    file_id: UUID
    page_no: int
    candidate_id: UUID
