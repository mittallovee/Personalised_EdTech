"""Possible duplicates of a question, from the bank index (D-16, M4 design note §7.4).

**Exact**: another question with the same ``duplicate_key`` (same format, stem, options and answer).
**Near**: another question whose ``match_text`` (stem and options, no solution) has a trigram
similarity of at least ``NEAR_SIMILARITY``, found through the trigram index, closest first.

Only this coaching's questions, never an archived one, never the question itself, and only those
the person asking may read (the bank's visibility rule), so a private draft is never offered as a
candidate to someone who may not open it. At most ``MAX_CANDIDATES`` of each kind.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg.errors import QueryCanceled
from sqlalchemy import Integer, cast, func, literal, or_, select, text, true
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.permissions import Action, require
from qbank.modules.search.models import BankRow
from qbank.modules.search.service import BankFilters, SearchTimedOut, _conditions

MAX_CANDIDATES = 20
# Set from the labelled sample in tests/fixtures/duplicate_sample.json (made-up pairs): the same
# question with a small change scores 0.83 to 1.00, a different question on the same topic 0.35 to
# 0.65. 0.75 is in the middle of the gap. A first value, not a measured accuracy.
NEAR_SIMILARITY = "0.75"


@dataclass(frozen=True, slots=True)
class DuplicateCandidate:
    master_id: UUID
    code: str
    state: str
    exact: bool
    similarity_percent: int  # 0 to 100, how alike the two texts are
    preview: str


def find_duplicates(
    session: Session,
    principal: Principal,
    *,
    master_id: UUID,
    key: str | None,
    text_to_match: str,
    timeout_ms: int,
) -> list[DuplicateCandidate]:
    """Exact duplicates first (newest first), then near ones (closest first)."""
    require(principal, Action.CREATE_QUESTIONS)
    where = [*_conditions(principal, BankFilters()), BankRow.master_id != master_id]
    similarity: Any = (
        cast(func.round(func.similarity(BankRow.match_text, literal(text_to_match)) * 100), Integer)
        if text_to_match
        else literal(0)
    )
    session.execute(
        text(
            "SELECT set_config('statement_timeout', :timeout, true),"
            " set_config('pg_trgm.similarity_threshold', :similarity, true)"
        ),
        {"timeout": str(timeout_ms), "similarity": NEAR_SIMILARITY},
    )
    try:
        exact = (
            list(
                session.execute(
                    select(BankRow, similarity)
                    .where(*where, BankRow.duplicate_key == key)
                    .order_by(BankRow.updated_at.desc(), BankRow.master_id.desc())
                    .limit(MAX_CANDIDATES)
                )
            )
            if key is not None
            else []
        )
        near = (
            list(
                session.execute(
                    select(BankRow, similarity)
                    .where(
                        *where,
                        BankRow.match_text.bool_op("%")(literal(text_to_match)),
                        # Every exact copy, not only the ones shown: past the limit they are still
                        # exact, never "near".
                        or_(BankRow.duplicate_key.is_(None), BankRow.duplicate_key != key)
                        if key is not None
                        else true(),
                    )
                    .order_by(similarity.desc(), BankRow.master_id)
                    .limit(MAX_CANDIDATES)
                )
            )
            if text_to_match
            else []
        )
    except OperationalError as error:
        if isinstance(error.orig, QueryCanceled):
            raise SearchTimedOut(
                "Looking for duplicates took too long. Please try again in a moment."
            ) from error
        raise
    return [
        DuplicateCandidate(
            master_id=row.master_id,
            code=row.code,
            state=row.state,
            exact=is_exact,
            similarity_percent=int(percent),
            preview=row.preview,
        )
        for rows, is_exact in ((exact, True), (near, False))
        for row, percent in rows
    ]
