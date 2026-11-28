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
