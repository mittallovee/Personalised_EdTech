import unicodedata
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

from qbank.core.pagination import PageInfo
from qbank.modules.taxonomy.catalogues import LANGUAGE_TAGS

NodeKind = Literal["CLASS", "SUBJECT", "CHAPTER", "TOPIC", "SUBTOPIC"]
NodeState = Literal["ACTIVE", "DEPRECATED"]


def no_control_characters(text: str) -> str:
    """Refuse control characters (NUL, newline, tab, bell...). PostgreSQL cannot store NUL, and the
    others would break a one-line name in a picker. Zero-width joiners (category Cf), which Indian
    scripts need, are not control characters and stay allowed."""
    if any(unicodedata.category(char) == "Cc" for char in text):
        raise ValueError("Control characters (such as a new line or tab) are not allowed.")
    return text


# Text that is stored and shown on one line: names, labels, aliases, short codes, search words.
OneLine = Annotated[str, AfterValidator(no_control_characters)]
Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    AfterValidator(no_control_characters),
]


def _other_languages(labels: dict[str, str]) -> dict[str, str]:
    for tag in labels:
        if tag == "en":
            raise ValueError("The English name is `name`, not a label.")
        if tag not in LANGUAGE_TAGS:
            raise ValueError(f"'{tag}' is not a language of this app.")
    return labels


# Names in the other languages, keyed by language tag (hi, gu, bn, mr, te, ta).
Labels = Annotated[dict[str, Name], AfterValidator(_other_languages), Field(max_length=10)]


class CreateNode(BaseModel):
    kind: NodeKind
    parent_id: UUID | None = Field(
        default=None,
        description="The item it sits under (a subject sits under a class). None for a class.",
    )
    name: Name = Field(description="The English name.", examples=["Kinematics"])
    labels: Labels = Field(default_factory=dict)
    sort_order: int = Field(default=0, ge=0, le=100_000, description="Smaller comes first.")


class UpdateNode(BaseModel):
    name: Name | None = None
    labels: Labels | None = Field(
        default=None, description="Replaces all the other-language names when sent."
    )
    sort_order: int | None = Field(default=None, ge=0, le=100_000)


class NodeOut(BaseModel):
    id: UUID
    kind: NodeKind
    parent_id: UUID | None
    name: str
    labels: dict[str, str]
    state: NodeState = Field(description="DEPRECATED items cannot be chosen for new questions.")
    sort_order: int
    revision: int
    created_at: datetime
    updated_at: datetime


class NodePage(BaseModel):
    data: list[NodeOut]
    page: PageInfo


class LanguageOut(BaseModel):
    tag: str = Field(examples=["hi"])
    english_name: str
    native_name: str


class BloomLevelOut(BaseModel):
    key: str = Field(examples=["APPLY"])
    label: str


class DifficultyLevelOut(BaseModel):
    level: int = Field(ge=1, le=10)
    meaning: str


ShortCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
    AfterValidator(no_control_characters),
]
SourceKind = Literal["BOOK", "MODULE", "TEST_SERIES", "PYQ_PAPER", "OTHER"]


class CreateExam(BaseModel):
    name: Name = Field(examples=["JEE Main"])
    short_code: ShortCode | None = Field(default=None, examples=["JEEM"])


class UpdateExam(BaseModel):
    name: Name | None = None
    short_code: ShortCode | None = Field(
        default=None, description="Send null to remove the short code; leave it out to keep it."
    )


class ExamOut(BaseModel):
    id: UUID
    name: str
    short_code: str | None
    state: NodeState = Field(description="DEPRECATED exams cannot be chosen for new questions.")
    revision: int
    created_at: datetime
    updated_at: datetime


class ExamPage(BaseModel):
    data: list[ExamOut]
    page: PageInfo


class CreateSource(BaseModel):
    kind: SourceKind
    name: Name = Field(examples=["HC Verma, Concepts of Physics"])


class UpdateSource(BaseModel):
    name: Name | None = Field(default=None, description="The kind never changes.")


class SourceOut(BaseModel):
    id: UUID
    kind: SourceKind
    name: str
    state: NodeState = Field(description="DEPRECATED sources cannot be chosen for new questions.")
    revision: int
    created_at: datetime
    updated_at: datetime


class SourcePage(BaseModel):
    data: list[SourceOut]
    page: PageInfo


# The aliases of a concept: other ways to say its name. Capped so a picker stays readable.
Aliases = Annotated[list[Name], Field(max_length=10)]


class CreateConcept(BaseModel):
    subject_id: UUID = Field(description="The subject this concept belongs to; it never changes.")
    name: Name = Field(description="The English name.", examples=["Newton's second law"])
    labels: Labels = Field(default_factory=dict)
    aliases: Aliases = Field(default_factory=list, examples=[["Newton's 2nd law"]])


class UpdateConcept(BaseModel):
    name: Name | None = None
    labels: Labels | None = Field(
        default=None, description="Replaces all the other-language names when sent."
    )
    aliases: Aliases | None = Field(default=None, description="Replaces all the aliases when sent.")


class ConceptOut(BaseModel):
    id: UUID
    subject_id: UUID
    name: str
    labels: dict[str, str]
    aliases: list[str] = Field(description="In alphabetical order.")
    state: NodeState = Field(description="DEPRECATED concepts cannot be chosen for new questions.")
    revision: int
    created_at: datetime
    updated_at: datetime


class ConceptPage(BaseModel):
    data: list[ConceptOut]
    page: PageInfo


ImportStatus = Literal["NEW", "CHANGED", "UNCHANGED", "ERROR"]
ImportState = Literal["PREVIEWED", "APPLIED"]  # an expired preview is gone: 410, never shown


class ImportCounts(BaseModel):
    new: int = Field(description="Rows that would add something.")
    changed: int = Field(description="Rows that would fill in or change something that exists.")
    unchanged: int = Field(description="Rows that match what is already there.")
    error: int = Field(description="Rows that cannot be imported. Any of these blocks applying.")


class ImportOut(BaseModel):
    id: UUID
    file_name: str
    state: ImportState
    counts: ImportCounts
    can_apply: bool = Field(
        description="True when no row is an error and something would be added or changed."
    )
    created_at: datetime
    applied_at: datetime | None


class ImportRowOut(BaseModel):
    number: int = Field(description="The row's number in the file (the header is row 1).")
    kind: str
    path: str
    status: ImportStatus
    message: str | None = Field(description="For an error: why, in plain words.")
    sort_order: int | None
    labels: dict[str, str]
    aliases: list[str]


class ImportRowPage(BaseModel):
    data: list[ImportRowOut]
    page: PageInfo
