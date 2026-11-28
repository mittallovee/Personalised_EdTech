from datetime import datetime
from typing import Literal
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
