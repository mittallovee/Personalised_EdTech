from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from qbank.core.pagination import PageInfo


class BankItem(BaseModel):
    """One question as the bank shows it: the version everyone reads (the published one if there is
    one), with its labels. Open the question itself for the text."""

    question_id: UUID
    code: str
    author_id: UUID = Field(description="Whoever started the question.")
    state: str = Field(description="The workflow state of the version shown.")
    version_number: int = Field(description="2 or more once a correction has been published.")
    archived: bool
    has_published: bool = Field(description="Whether a version has been published.")
    has_open_correction: bool = Field(
        description="A correction of the published version is being worked on."
    )
    question_type: str | None
    language: str | None
    class_id: UUID | None
    subject_id: UUID | None = Field(description="Look the name up in the coaching's syllabus.")
    chapter_id: UUID | None
    topic_id: UUID | None
    primary_concept_id: UUID | None
    concept_ids: list[UUID] = Field(description="The main concept and the other concepts.")
    difficulty: int | None = Field(description="1 to 10.")
    bloom_level: str | None
    is_pyq: bool = Field(description="A past-year question.")
    exam_id: UUID | None
    exam_year: int | None
    has_solution: bool
    has_video: bool
    preview: str = Field(
        description="The beginning of the question's text (about 200 characters, plain text, with"
        " equations as their LaTeX). Empty until `qbank reindex-bank` has run once after 4f."
    )
    created_at: datetime
    updated_at: datetime = Field(
        description="When the question last changed, as the bank shows it."
    )


class BankPage(BaseModel):
    data: list[BankItem]
    page: PageInfo
    total: int = Field(
        ge=0,
        description="How many questions match the filters, not only the ones on this page. For a"
        " search (`q`) it is how many results are shown.",
    )
    truncated: bool = Field(
        default=False,
        description="A search (`q`) matched more questions than it shows: narrow it with a more"
        " specific word or a filter. Always false for the plain list, which has pages.",
    )
