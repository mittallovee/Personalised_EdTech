"""Golden sets and the measurement of extraction quality (M6 6j, G-11, K-14).

An admin collects reviewed questions into a named set: each case freezes what a person finished and
accepted from a page. A measurement reads those pages again with a chosen model and scores the
result against the key (``golden_score``); it is run before and after any change to the prompt or
the model, and what it finds is reported as it is.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, ValidationFailed
from qbank.core.permissions import Action, require
from qbank.core.storage import Missing, Storage
from qbank.modules.ai.public import AIProvider, ProviderError
from qbank.modules.audit.public import record_event
from qbank.modules.ingestion.extract import prompt
from qbank.modules.ingestion.extract.schema import BadPage, read_page
from qbank.modules.ingestion.golden_score import Report, score_page, summarise
from qbank.modules.ingestion.models import GoldenCase, GoldenSet, IngestCandidate, IngestPage

MOST_CASES_PER_SET = 500


def _org(principal: Principal) -> UUID:
    org = principal.tenant_context.organization_id
    if org is None:
        raise NotFound("No coaching.")
    return org


def create_set(
    session: Session, principal: Principal, name: str, *, request_id: str | None
) -> GoldenSet:
    require(principal, Action.MANAGE_INGEST)
    organization_id = _org(principal)
    cleaned = " ".join(name.split())
    if not cleaned or len(cleaned) > 120:
        raise ValidationFailed("Give the set a name of up to 120 characters.", code="NAME_INVALID")
    if session.scalar(select(GoldenSet.id).where(GoldenSet.name == cleaned)) is not None:
        raise Conflict("A set with this name already exists.", code="GOLDEN_SET_EXISTS")
    row = GoldenSet(organization_id=organization_id, name=cleaned, created_by=principal.user_id)
    session.add(row)
    session.flush()
    record_event(
        session,
        action="GOLDEN_SET_CREATED",
        entity_type="golden_set",
        entity_id=row.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        request_id=request_id,
        after={"name": cleaned},
    )
    return row


def list_sets(session: Session, principal: Principal) -> list[tuple[GoldenSet, int]]:
    require(principal, Action.MANAGE_INGEST)
    counts = {
        set_id: n
        for set_id, n in session.execute(
            select(GoldenCase.set_id, func.count()).group_by(GoldenCase.set_id)
        )
    }
    rows = session.scalars(select(GoldenSet).order_by(GoldenSet.name))
    return [(row, counts.get(row.id, 0)) for row in rows]


def add_case(
    session: Session,
    principal: Principal,
    set_id: UUID,
    candidate_id: UUID,
    *,
    request_id: str | None,
) -> GoldenCase:
    """Freeze a question a person accepted as part of the key. Only an accepted candidate counts:
    a person has finished it, so it is what the page should have produced."""
    require(principal, Action.MANAGE_INGEST)
    organization_id = _org(principal)
    golden = session.get(GoldenSet, set_id)
    candidate = session.get(IngestCandidate, candidate_id)
    if golden is None or candidate is None:
        raise NotFound("No such set or candidate.")
    if candidate.state != "ACCEPTED":
        raise Conflict(
            "Only a question that was accepted can be part of the key.", code="GOLDEN_NOT_ACCEPTED"
        )
    held = session.scalar(
        select(func.count()).select_from(GoldenCase).where(GoldenCase.set_id == set_id)
    )
    if (held or 0) >= MOST_CASES_PER_SET:
        raise Conflict("This set is full.", code="GOLDEN_SET_FULL")
    if session.scalar(
        select(GoldenCase.id).where(
            GoldenCase.set_id == set_id, GoldenCase.candidate_id == candidate_id
        )
    ):
        raise Conflict("This question is already in the set.", code="GOLDEN_CASE_EXISTS")
    row = GoldenCase(
        organization_id=organization_id,
        set_id=set_id,
        file_id=candidate.file_id,
        page_no=candidate.page_no,
        candidate_id=candidate_id,
        expected=dict(candidate.content),
        created_by=principal.user_id,
    )
    session.add(row)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:  # a simultaneous add of the same question won the race
        raise Conflict("This question is already in the set.", code="GOLDEN_CASE_EXISTS") from None
    record_event(
        session,
        action="GOLDEN_CASE_ADDED",
        entity_type="golden_set",
        entity_id=set_id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        request_id=request_id,
        after={"candidate": str(candidate_id), "file_id": str(candidate.file_id)},
    )
    return row


@dataclass(frozen=True, slots=True)
class PageRead:
    """What reading one page gave: the questions as content, the tokens used, or a failure."""

    questions: list[dict[str, Any]]
    tokens_in: int = 0
    tokens_out: int = 0
    failed: bool = False


def measure(cases: list[GoldenCase], read: Callable[[UUID, int], PageRead]) -> Report:
    """Read each distinct page of the key once, and score every key question on it. A page that
    cannot be read counts all its key questions as not found, and is reported."""
    pages: dict[tuple[UUID, int], list[GoldenCase]] = {}
    for case in cases:
        pages.setdefault((case.file_id, case.page_no), []).append(case)
    results = []
    extra = failed = tokens_in = tokens_out = 0
    for (file_id, page_no), keys in sorted(pages.items(), key=lambda p: (str(p[0][0]), p[0][1])):
        got = read(file_id, page_no)
        tokens_in, tokens_out = tokens_in + got.tokens_in, tokens_out + got.tokens_out
        failed += 1 if got.failed else 0
        scored, more = score_page([dict(k.expected) for k in keys], got.questions)
        results.extend(scored)
        extra += more
    return summarise(
        results, extra=extra, pages_failed=failed, tokens_in=tokens_in, tokens_out=tokens_out
    )


def live_reader(
    session: Session, storage: Storage, provider: AIProvider, api_key: str, model_id: str
) -> Callable[[UUID, int], PageRead]:
    """Read a stored page with a real model, the way a normal reading does (same prompt, same
    locked format), but with no person's budget: the command is run on purpose by the owner, and
    the report states the tokens used."""

    def read(file_id: UUID, page_no: int) -> PageRead:
        page = session.scalar(
            select(IngestPage).where(IngestPage.file_id == file_id, IngestPage.page_no == page_no)
        )
        if page is None:
            return PageRead([], failed=True)
        keys = [page.image_key, *(str(f["key"]) for f in (page.figures or []) if "key" in f)]
        try:
            pictures = tuple(storage.get(key) for key in keys if key is not None)
        except Missing:
            return PageRead([], failed=True)
        request = prompt.build_request(
            model_id=model_id, page_no=page_no, text=page.text, pictures=pictures
        )
        try:
            result = provider.generate_structured(api_key, request)
            reading = read_page(result.data)
        except ProviderError, BadPage:
            return PageRead([], failed=True)
        return PageRead(
            [dict(c.content) for c in reading.candidates],
            result.tokens_in or 0,
            result.tokens_out or 0,
        )

    return read
