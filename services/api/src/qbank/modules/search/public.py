"""Public interface of the search module. Other modules import only from here."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from qbank.modules.search.duplicates import (
    MAX_CANDIDATES,
    NEAR_SIMILARITY,
    DuplicateCandidate,
    find_duplicates,
    shared_codes,
    shared_exact_duplicates,
)
from qbank.modules.search.models import BankRow

__all__ = [
    "MAX_CANDIDATES",
    "NEAR_SIMILARITY",
    "BankEntry",
    "DuplicateCandidate",
    "find_duplicates",
    "save_entry",
    "shared_codes",
    "shared_exact_duplicates",
]


@dataclass(frozen=True, slots=True)
class BankEntry:
    """One row of the bank index, as the questions module works it out from a question's tables.

    Every field is derived from the question, so two ways of getting it (the incremental write and
    the rebuild) must agree: a test compares them."""

    organization_id: UUID
    master_id: UUID
    code: str
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    version_number: int
    state: str
    is_private: bool
    is_archived: bool
    has_published: bool
    has_open_correction: bool
    has_solution: bool
    has_video: bool
    is_pyq: bool = False
    question_type: str | None = None
    language: str | None = None
    class_id: UUID | None = None
    subject_id: UUID | None = None
    chapter_id: UUID | None = None
    topic_id: UUID | None = None
    primary_concept_id: UUID | None = None
    concept_ids: tuple[UUID, ...] = field(default_factory=tuple)
    difficulty: int | None = None
    bloom_level: str | None = None
    exam_id: UUID | None = None
    exam_year: int | None = None
    stem_text: str = ""  # everything a search reads, as one line of plain text (F-03)
    preview: str = ""  # the beginning of the stem, for the list
    duplicate_key: str | None = None  # the same for two exact duplicates (D-16)
    match_text: str = ""  # what a near-duplicate check compares: stem and options, no solution


_KEYS = ("organization_id", "master_id")


def save_entry(session: Session, entry: BankEntry) -> None:
    """Write the question's row, in the caller's transaction, so it commits or rolls back with the
    change that caused it. A row that already says the same is left untouched."""
    values = asdict(entry)
    values["concept_ids"] = list(entry.concept_ids)
    statement = insert(BankRow).values(values)
    columns = [key for key in values if key not in _KEYS]
    session.execute(
        statement.on_conflict_do_update(
            index_elements=list(_KEYS),
            set_={key: statement.excluded[key] for key in columns},
            where=or_(
                *(
                    BankRow.__table__.c[key].is_distinct_from(statement.excluded[key])
                    for key in columns
                )
            ),
        )
    )
