"""The translation glossary (M5 design note §10; H-14, prompt spec PL-13).

An admin lists the terms a coaching wants translated one fixed way, per target language. A
translation run receives the entries that matter for the question in front of it, as data inside the
prompt (never as instructions). Terms are unique per language ignoring case.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, PreconditionFailed, ValidationFailed
from qbank.core.etag import etag, require_if_match
from qbank.core.permissions import Action, require
from qbank.modules.ai.models import GlossaryEntry
from qbank.modules.audit.public import record_event
from qbank.modules.taxonomy.public import language_names

ENTITY_TYPE = "glossary_entry"
MOST_ENTRIES = 2000  # per coaching and language
MOST_SHOWN = 100  # entries sent in one prompt
MOST_SHOWN_CHARS = 6000


def _org(principal: Principal) -> UUID:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise PreconditionFailed("No coaching to change the glossary of.")
    return organization_id


def _check_language(language: str) -> None:
    if language not in language_names():
        raise ValidationFailed(
            "That is not one of the question languages.", code="AI_GLOSSARY_LANGUAGE_INVALID"
        )


def _clean(value: str) -> str:
    return " ".join(value.split())  # one space between words, none at the ends


def _facts(entry: GlossaryEntry) -> dict[str, object]:
    return {
        "language": entry.language,
        "source_term": entry.source_term,
        "target_term": entry.target_term,
        "note": entry.note,
    }


def _audit(
    session: Session,
    principal: Principal,
    entry: GlossaryEntry,
    action: str,
    request_id: str | None,
    before: dict[str, object] | None,
    after: dict[str, object] | None,
) -> None:
    record_event(
        session,
        action=action,
        entity_type=ENTITY_TYPE,
        entity_id=entry.id,
        organization_id=entry.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before=before,
        after=after,
    )


def list_entries(
    session: Session, principal: Principal, *, language: str | None = None
) -> list[GlossaryEntry]:
    require(principal, Action.MANAGE_AI_SETTINGS)
    query = select(GlossaryEntry).where(GlossaryEntry.organization_id == _org(principal))
    if language is not None:
        query = query.where(GlossaryEntry.language == language)
    return list(
        session.scalars(
            query.order_by(GlossaryEntry.language, func.lower(GlossaryEntry.source_term))
        )
    )


def create_entry(
    session: Session,
    principal: Principal,
    *,
    language: str,
    source_term: str,
    target_term: str,
    note: str | None,
    request_id: str | None,
) -> GlossaryEntry:
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = _org(principal)
    _check_language(language)
    source, target = _clean(source_term), _clean(target_term)
    if not source or not target:
        raise ValidationFailed("Both terms are needed.", code="AI_GLOSSARY_TERM_EMPTY")
    count = session.scalar(
        select(func.count())
        .select_from(GlossaryEntry)
        .where(GlossaryEntry.organization_id == organization_id, GlossaryEntry.language == language)
    )
    if (count or 0) >= MOST_ENTRIES:
        raise Conflict(
            f"A language can have at most {MOST_ENTRIES} terms.", code="AI_GLOSSARY_FULL"
        )
    entry = GlossaryEntry(
        organization_id=organization_id,
        language=language,
        source_term=source,
        target_term=target,
        note=_clean(note) if note else None,
        created_by=principal.user_id,
        updated_by=principal.user_id,
    )
    try:
        with session.begin_nested():
            session.add(entry)
            session.flush()
    except IntegrityError:
        raise Conflict(
            "This term already has an entry in that language. Change that one instead.",
            code="AI_GLOSSARY_DUPLICATE",
        ) from None
    _audit(session, principal, entry, "AI_GLOSSARY_ADDED", request_id, None, _facts(entry))
    return entry


def _locked(session: Session, organization_id: UUID, entry_id: UUID) -> GlossaryEntry:
    entry = session.scalars(
        select(GlossaryEntry)
        .where(GlossaryEntry.id == entry_id, GlossaryEntry.organization_id == organization_id)
        .with_for_update()
    ).first()
    if entry is None:
        raise NotFound("No such glossary entry.")
    return entry


def update_entry(
    session: Session,
    principal: Principal,
    entry_id: UUID,
    *,
    source_term: str,
    target_term: str,
    note: str | None,
    if_match: str | None,
    request_id: str | None,
) -> GlossaryEntry:
    """Change the terms or the note of an entry (its language stays)."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    entry = _locked(session, _org(principal), entry_id)
    require_if_match(if_match, entry.revision)
    source, target = _clean(source_term), _clean(target_term)
    if not source or not target:
        raise ValidationFailed("Both terms are needed.", code="AI_GLOSSARY_TERM_EMPTY")
    before = _facts(entry)
    entry.source_term, entry.target_term = source, target
    entry.note = _clean(note) if note else None
    if _facts(entry) == before:
        return entry
    entry.revision += 1
    entry.updated_by = principal.user_id
    entry.updated_at = datetime.now(UTC)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raise Conflict(
            "This term already has an entry in that language.", code="AI_GLOSSARY_DUPLICATE"
        ) from None
    _audit(session, principal, entry, "AI_GLOSSARY_CHANGED", request_id, before, _facts(entry))
    return entry


def delete_entry(
    session: Session,
    principal: Principal,
    entry_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
) -> None:
    require(principal, Action.MANAGE_AI_SETTINGS)
    entry = _locked(session, _org(principal), entry_id)
    require_if_match(if_match, entry.revision)
    before = _facts(entry)
    _audit(session, principal, entry, "AI_GLOSSARY_REMOVED", request_id, before, None)
    session.delete(entry)
    session.flush()


def current_etag(entry: GlossaryEntry) -> str:
    return etag(entry.revision)


@dataclass(frozen=True, slots=True)
class Term:
    source: str
    target: str
    note: str | None


def terms_for(
    session: Session, organization_id: UUID, language: str, *, text: str | None = None
) -> list[Term]:
    """The entries for a target language, for a translation prompt. Given the question's ``text``
    only the entries whose source term appears in it (ignoring case) are returned, longest term
    first, so the prompt stays small. Needs no permission: the orchestrator has already checked
    who may run the translation. Always limited to the one coaching."""
    rows = session.scalars(
        select(GlossaryEntry).where(
            GlossaryEntry.organization_id == organization_id, GlossaryEntry.language == language
        )
    )
    lowered = text.lower() if text is not None else None
    found = [
        Term(row.source_term, row.target_term, row.note)
        for row in rows
        if lowered is None or row.source_term.lower() in lowered
    ]
    found.sort(key=lambda term: (-len(term.source), term.source.lower()))
    return found


def render_terms(terms: list[Term]) -> str:
    """The glossary as lines of ``source = target`` (and the note in brackets), cut to a size a
    prompt can carry. Empty when there is nothing to say."""
    lines: list[str] = []
    used = 0
    for term in terms[:MOST_SHOWN]:
        line = f"{term.source} = {term.target}" + (f" ({term.note})" if term.note else "")
        if used + len(line) + 1 > MOST_SHOWN_CHARS:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)
