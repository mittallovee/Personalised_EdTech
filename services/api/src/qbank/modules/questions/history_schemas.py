"""What the history and diff routes send (API style guide)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from qbank.modules.questions.domain.diff import Op, SegmentKind
from qbank.modules.questions.history import HistoryKind


class HistoryEntry(BaseModel):
    kind: HistoryKind = Field(
        description="What happened: the start of the question, a saved checkpoint, a review step,"
        " the start of a correction, archive or restore."
    )
    at: datetime
    actor_id: UUID | None = Field(description="Who did it.")
    version_number: int | None = Field(
        description="The version it belongs to (1, or 2 and up for a correction); empty for"
        " archive and restore, which concern the whole question."
    )
    revision_id: UUID | None = Field(
        description="The saved text the entry is about; pass it to the diff route to compare it"
        " with another."
    )
    reasons: list[str] = Field(description="For a return: the reason codes chosen.")
    note: str | None = Field(description="For a return: the reviewer's note.")


class HistoryOut(BaseModel):
    data: list[HistoryEntry] = Field(description="Oldest first.")


class SegmentOut(BaseModel):
    kind: SegmentKind
    text: str


class ChangeOut(BaseModel):
    op: Op
    path: list[str | int] = Field(
        description="Where in the content: object keys and list positions, e.g."
        ' `["options", 2, "content", 0, "text"]`. Positions count as the changes are applied'
        " in the order listed."
    )
    before: Any = Field(default=None, description="The old value (`remove` and `replace`).")
    after: Any = Field(default=None, description="The new value (`add` and `replace`).")
    segments: list[SegmentOut] | None = Field(
        default=None,
        description="For a changed text: its words, each `equal`, `insert` or `delete`. Show"
        " them as text with marks; never as HTML.",
    )


class DiffRevision(BaseModel):
    id: UUID
    version_number: int
    number: int = Field(description="Counts up within the version.")
    frozen_at: datetime | None = Field(description="Empty for the text still being edited.")


class DiffOut(BaseModel):
    from_revision: DiffRevision
    to_revision: DiffRevision
    identical: bool
    changes: list[ChangeOut] = Field(
        description="What turns the first text into the second. Equations, pictures, tables and"
        " lists count as single items: a changed one is replaced as a whole."
    )
