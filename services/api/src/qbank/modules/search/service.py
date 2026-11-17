"""Reading the bank: the list with its filters and total, one question by its code, and a search of
the words in the questions (F-01, F-02, F-03).

What a person may see is decided in the query, once, by ``_readable``: work in progress (a draft, a
returned question) is read by its author, admins and edit-others holders, and to anyone else it does
not exist, so it is never listed, counted or found by its code. The rule is the questions module's
(``questions/visibility.py``), written here over the row's own ``is_private`` and ``created_by``; a
test checks that the two agree for every state and role.
"""

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.errors import QueryCanceled
from sqlalchemy import (
    ColumnElement,
    false,
    func,
    literal,
    literal_column,
    or_,
    select,
    text,
    true,
    tuple_,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.codes import normalize_code
from qbank.core.errors import AppError, MalformedRequest, NotFound
from qbank.core.permissions import Action, is_allowed, may_access_all_drafts, require
from qbank.modules.search.models import BankRow, BankWord


@dataclass(frozen=True, slots=True)
class BankFilters:
    """What to narrow the bank by. Filters combine with AND; the values of one filter with OR, and
    a left-out filter does not narrow. ``archived`` picks the archive instead of the live bank."""

    class_ids: tuple[UUID, ...] = ()
    subject_ids: tuple[UUID, ...] = ()
    chapter_ids: tuple[UUID, ...] = ()
    topic_ids: tuple[UUID, ...] = ()
    concept_ids: tuple[UUID, ...] = ()  # the main concept or any other concept
    difficulties: tuple[int, ...] = ()
    bloom_levels: tuple[str, ...] = ()
    question_types: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    exam_ids: tuple[UUID, ...] = ()
    exam_years: tuple[int, ...] = ()
    states: tuple[str, ...] = ()
    author_ids: tuple[UUID, ...] = ()
    is_pyq: bool | None = None
    has_solution: bool | None = None
    has_video: bool | None = None
    archived: bool = False


@dataclass(frozen=True, slots=True)
class BankPage:
    rows: list[BankRow]
    has_more: bool
    total: int
    truncated: bool = False  # a search matched more than it shows: narrow it


class SearchTimedOut(AppError):
    """A search ran past its time limit; the database stopped it."""

    status_code = 503
    code = "SEARCH_TIMED_OUT"


def _readable(principal: Principal) -> ColumnElement[bool]:
    if not is_allowed(principal, Action.CREATE_QUESTIONS):
        return false()
    if may_access_all_drafts(principal):
        return true()
    return or_(BankRow.is_private.is_(False), BankRow.created_by == principal.user_id)


def _conditions(principal: Principal, filters: BankFilters) -> list[ColumnElement[bool]]:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise NotFound("No such question.")
    # Row-level security already keeps to this coaching; saying so here as well costs nothing.
    found = [
        BankRow.organization_id == organization_id,
        _readable(principal),
        BankRow.is_archived.is_(filters.archived),
    ]
    one_of: list[tuple[Any, tuple[Any, ...]]] = [
        (BankRow.class_id, filters.class_ids),
        (BankRow.subject_id, filters.subject_ids),
        (BankRow.chapter_id, filters.chapter_ids),
        (BankRow.topic_id, filters.topic_ids),
        (BankRow.difficulty, filters.difficulties),
        (BankRow.bloom_level, filters.bloom_levels),
        (BankRow.question_type, filters.question_types),
        (BankRow.language, tuple(value.lower() for value in filters.languages)),
        (BankRow.exam_id, filters.exam_ids),
        (BankRow.exam_year, filters.exam_years),
        (BankRow.state, filters.states),
        (BankRow.created_by, filters.author_ids),
    ]
    found += [column.in_(values) for column, values in one_of if values]
    if filters.concept_ids:
        found.append(BankRow.concept_ids.overlap(list(filters.concept_ids)))
    flags = (
        (BankRow.is_pyq, filters.is_pyq),
        (BankRow.has_solution, filters.has_solution),
        (BankRow.has_video, filters.has_video),
    )
    found += [column.is_(wanted) for column, wanted in flags if wanted is not None]
    return found


def list_bank(
    session: Session,
    principal: Principal,
    filters: BankFilters,
    *,
    limit: int,
    after: tuple[datetime, UUID] | None,
) -> BankPage:
    """One page of the bank, the most recently changed first, after ``after`` (a cursor), with the
    number of questions that match the same filters and visibility, so the number on the screen is
    the number of matches."""
    require(principal, Action.CREATE_QUESTIONS)
    where = _conditions(principal, filters)
    total = session.scalar(select(func.count()).select_from(BankRow).where(*where)) or 0
    query = select(BankRow).where(*where)
    if after is not None:
        query = query.where(tuple_(BankRow.updated_at, BankRow.master_id) < after)
    found = list(
        session.scalars(
            query.order_by(BankRow.updated_at.desc(), BankRow.master_id.desc()).limit(limit + 1)
        )
    )
    return BankPage(rows=found[:limit], has_more=len(found) > limit, total=total)


def find_by_code(session: Session, principal: Principal, typed_code: str) -> BankRow:
    """The question with this code (lower case, spaces and dashes forgiven). Another coaching's
    code, a missing one and a private draft that is not yours answer the same: not found."""
    require(principal, Action.CREATE_QUESTIONS)
    code = normalize_code(typed_code)
    row = session.scalars(
        select(BankRow).where(*_conditions(principal, BankFilters()), BankRow.code == code)
    ).first()
    if row is None:
        # An archived question is still found by its code: a person pasting a code wants it.
        row = session.scalars(
            select(BankRow).where(
                *_conditions(principal, BankFilters(archived=True)), BankRow.code == code
            )
        ).first()
    if row is None:
        raise NotFound("No such question.")
    return row


# ---- free-text search (F-03) --------------------------------------------------------------------

SEARCH_MAX = 100  # a ranked list has no deep pages: at most this many results
FALLBACK_BELOW = 10  # fewer exact-word matches than this and the close matches are added
# How close a word of the bank must be to a typed word to count as that word with a typo (0 to 1,
# trigram similarity of the two words). Measured (docs/operations/load-tests.md): typos of
# acceleration, velocity, pendulum, frequency, gravity and momentum score 0.50 to 0.67, a plural
# ("forces" for "force") 0.63, and different words (forest/force, block/black, mass/pass) 0.25 to
# 0.33.
SIMILARITY = "0.45"
CLOSE_WORDS = 3  # bank words tried in place of each typed word, closest first
MAX_TYPED_WORDS = 8  # words of a search given close alternatives; the rest must match exactly
_REGCONFIG: ColumnElement[Any] = literal_column("'simple'::regconfig")


def clean_words(typed: str) -> str:
    """What was typed, as one line in Unicode's composed form, so the same Hindi word typed on two
    keyboards is the same word. A NUL character (which text cannot hold) is a space."""
    return " ".join(unicodedata.normalize("NFC", typed).replace("\x00", " ").split())


def search_bank(
    session: Session,
    principal: Principal,
    filters: BankFilters,
    typed: str,
    *,
    limit: int,
    timeout_ms: int,
) -> BankPage:
    """The questions that match the words typed, best match first, narrowed by the filters.

    Exact words come first, ranked by how well they match. When fewer than ``FALLBACK_BELOW`` match
    exactly, questions with a close word (a typo, "acceleratoin") follow, best match first, unless
    the search is a quoted phrase or leaves a word out, which ask for exactness. The same
    visibility and filters as the list apply to both, so a private draft is never a search hit. At
    most ``limit`` (and never more than ``SEARCH_MAX``) come back and ``truncated`` says whether
    more matched; a ranked list has no next page. The database stops a search after ``timeout_ms``.
    """
    require(principal, Action.CREATE_QUESTIONS)
    words = clean_words(typed)
    if not words:
        raise MalformedRequest("Type a word or two to search for.")
    shown = min(limit, SEARCH_MAX)
    where = _conditions(principal, filters)
    # Both settings last until the transaction ends. A bound value, never text built into the query.
    session.execute(
        text(
            "SELECT set_config('statement_timeout', :timeout, true),"
            " set_config('pg_trgm.similarity_threshold', :similarity, true)"
        ),
        {"timeout": str(timeout_ms), "similarity": SIMILARITY},
    )
    try:
        found = _exact_matches(session, where, words, shown + 1)
        if len(found) < FALLBACK_BELOW and not _asks_for_precision(words):
            found += _close_matches(session, principal, where, words, shown + 1 - len(found), found)
    except OperationalError as error:
        if isinstance(error.orig, QueryCanceled):
            raise SearchTimedOut(
                "That search took too long. Add a filter or a more specific word."
            ) from error
        raise
    rows = found[:shown]
    return BankPage(rows=rows, has_more=False, total=len(rows), truncated=len(found) > shown)


def _asks_for_precision(words: str) -> bool:
    """A quoted phrase or a word left out (``-word``) says exactly what is wanted: a close word
    would ignore it, so those searches match exactly or not at all."""
    return '"' in words or any(word.startswith("-") for word in words.split())


def _exact_matches(
    session: Session, where: list[ColumnElement[bool]], words: str, count: int
) -> list[BankRow]:
    # ``websearch_to_tsquery`` reads what a person types ("quoted phrase", -not, or) and never fails
    # on it: nothing typed can become query syntax.
    query = func.websearch_to_tsquery(_REGCONFIG, words)
    return list(
        session.scalars(
            select(BankRow)
            .where(*where, BankRow.search_vector.bool_op("@@")(query))
            .order_by(
                func.ts_rank(BankRow.search_vector, query).desc(),
                BankRow.updated_at.desc(),
                BankRow.master_id.desc(),
            )
            .limit(count)
        )
    )


def _close_matches(
    session: Session,
    principal: Principal,
    where: list[ColumnElement[bool]],
    words: str,
    count: int,
    already: list[BankRow],
) -> list[BankRow]:
    """Questions that match when each typed word may also be a close word of this coaching's bank.

    A typo is matched against the coaching's list of words (``bank_words``, a few thousand), not
    against the text of every question, which took seconds on 100,000 questions; the words found
    are then searched with the word index like any other search."""
    query = _close_query(session, principal.tenant_context.organization_id, words)
    if query is None:
        return []
    return list(
        session.scalars(
            select(BankRow)
            .where(
                *where,
                BankRow.search_vector.bool_op("@@")(query),
                BankRow.master_id.not_in([row.master_id for row in already]),
            )
            .order_by(
                func.ts_rank(BankRow.search_vector, query).desc(),
                BankRow.updated_at.desc(),
                BankRow.master_id.desc(),
            )
            .limit(count)
        )
    )


def _close_query(
    session: Session, organization_id: UUID | None, words: str
) -> ColumnElement[Any] | None:
    """Every typed word, or one of its close words, must be there: ``(w1 | a | b) & (w2 | c)``.
    ``None`` when no typed word has a close word (the exact search already said everything)."""
    typed = list(
        session.scalars(
            text("SELECT lexeme FROM unnest(to_tsvector('simple', :words))"), {"words": words}
        )
    )
    query: ColumnElement[Any] | None = None
    widened = False
    for position, word in enumerate(typed):
        either = _word(word)
        # Every word stays required; only the first few are looked up, so the work is bounded.
        alternatives = (
            _close_words(session, organization_id, word) if position < MAX_TYPED_WORDS else []
        )
        for close in alternatives:
            either = either.op("||")(_word(close))
            widened = True
        query = either if query is None else query.op("&&")(either)
    return query if widened else None


def _close_words(session: Session, organization_id: UUID | None, word: str) -> list[str]:
    if len(word) < 3:  # too short to tell a typo from another word
        return []
    # ``%`` is "similar enough" (pg_trgm.similarity_threshold), which the trigram index answers.
    return list(
        session.scalars(
            select(BankWord.word)
            .where(
                BankWord.organization_id == organization_id,  # row-level security says so too
                BankWord.word.bool_op("%")(word),
                BankWord.word != word,
            )
            .order_by(func.similarity(BankWord.word, word).desc(), BankWord.word)
            .limit(CLOSE_WORDS)
        )
    )


def _word(word: str) -> ColumnElement[Any]:
    # One word as a query, from a bound value: never query syntax.
    return func.plainto_tsquery(_REGCONFIG, literal(word))
