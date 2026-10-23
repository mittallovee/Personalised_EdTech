"""Concepts (M3 design note §4.2): what a question is about, with other-language names and aliases.

A concept belongs to one subject and never changes subject. Within a subject its name and its
aliases are all different from each other: one name or alias points at one concept, so a later
match (the AI of M5, or a search) is never ambiguous. Everything that writes concepts of a subject
first locks that subject row, so two admins cannot slip a clash past the checks at the same time.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, ValidationFailed
from qbank.core.etag import require_if_match
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.core.permissions import Action, require
from qbank.modules.audit.public import record_event
from qbank.modules.taxonomy.catalogues import name_key
from qbank.modules.taxonomy.cursors import encode_cursor
from qbank.modules.taxonomy.models import Concept, ConceptAlias, ConceptLabel, TaxonomyNode
from qbank.modules.taxonomy.schemas import ConceptOut, CreateConcept, UpdateConcept

_UNIQUE_INDEXES = ("concepts_name", "concept_aliases_key")


def _acting(principal: Principal) -> bool:
    return principal.acting_organization_id is not None


def _organization_id(principal: Principal) -> UUID:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise NotFound("No such concept.")
    return organization_id


# --- Reading ----------------------------------------------------------------------------------


def next_cursor(concepts: Sequence[Concept], has_more: bool) -> str | None:
    if not (has_more and concepts):
        return None
    return encode_cursor(0, concepts[-1].name_key, concepts[-1].id)  # no sort order here


def list_concepts(
    session: Session,
    *,
    subject_id: UUID | None,
    state: str | None,
    text: str | None,
    limit: int,
    after: tuple[int, str, UUID] | None,
) -> tuple[list[Concept], bool]:
    """In name order. ``text`` finds concepts whose name or an alias contains it (any case or
    spacing); it is matched as plain text, so ``%`` and ``_`` mean themselves."""
    query = select(Concept).order_by(Concept.name_key, Concept.id)
    if subject_id is not None:
        query = query.where(Concept.subject_id == subject_id)
    if state is not None:
        query = query.where(Concept.state == state)
    if text is not None:
        key = name_key(text)
        query = query.where(
            or_(
                Concept.name_key.contains(key, autoescape=True),
                exists().where(
                    ConceptAlias.concept_id == Concept.id,
                    ConceptAlias.alias_key.contains(key, autoescape=True),
                ),
            )
        )
    if after is not None:
        _, last_key, last_id = after
        query = query.where(
            (Concept.name_key > last_key)
            | ((Concept.name_key == last_key) & (Concept.id > last_id))
        )
    rows = list(session.scalars(query.limit(limit + 1)))
    return rows[:limit], len(rows) > limit


def get_concept(session: Session, concept_id: UUID) -> Concept:
    concept = session.get(Concept, concept_id)  # row-level security hides other coachings'
    if concept is None:
        raise NotFound("No such concept.")
    return concept


def describe(session: Session, concepts: Sequence[Concept]) -> list[ConceptOut]:
    labels: dict[UUID, dict[str, str]] = {concept.id: {} for concept in concepts}
    aliases: dict[UUID, list[str]] = {concept.id: [] for concept in concepts}
    if concepts:
        ids = list(labels)
        for label in session.scalars(select(ConceptLabel).where(ConceptLabel.concept_id.in_(ids))):
            labels[label.concept_id][label.language] = label.label
        rows = session.scalars(
            select(ConceptAlias)
            .where(ConceptAlias.concept_id.in_(ids))
            .order_by(ConceptAlias.alias_key)
        )
        for alias in rows:
            aliases[alias.concept_id].append(alias.alias)
    return [
        ConceptOut(
            id=concept.id,
            subject_id=concept.subject_id,
            name=concept.name,
            labels=labels[concept.id],
            aliases=aliases[concept.id],
            state=concept.state,
            revision=concept.revision,
            created_at=concept.created_at,
            updated_at=concept.updated_at,
        )
        for concept in concepts
    ]


# --- Changing ---------------------------------------------------------------------------------


def _snapshot(session: Session, concept: Concept) -> dict[str, Any]:
    aliases = session.scalars(
        select(ConceptAlias.alias)
        .where(ConceptAlias.concept_id == concept.id)
        .order_by(ConceptAlias.alias_key)
    )
    labels = {
        label.language: label.label
        for label in session.scalars(
            select(ConceptLabel).where(ConceptLabel.concept_id == concept.id)
        )
    }
    return {
        "subject_id": str(concept.subject_id),
        "name": concept.name,
        "labels": dict(sorted(labels.items())),
        "aliases": list(aliases),
        "state": concept.state,
    }


def _save(session: Session) -> None:
    """Flush, turning "this name is taken" into a clear 409."""
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as error:
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint in _UNIQUE_INDEXES:
            raise Conflict(
                "Another concept or alias in this subject already uses this name.",
                code="DUPLICATE_NAME",
            ) from None
        raise


def _lock_subject(session: Session, subject_id: UUID) -> TaxonomyNode:
    """The subject, locked until the transaction ends. Every write to the concepts of a subject
    starts here, so they run one after another and their clash checks cannot interleave."""
    subject = session.scalars(
        select(TaxonomyNode).where(TaxonomyNode.id == subject_id).with_for_update()
    ).first()
    if subject is None:
        raise NotFound("No such subject.")
    return subject


def _unique_aliases(aliases: Sequence[str]) -> dict[str, str]:
    """The aliases by key, the first spelling of each (two spellings of one name are one alias)."""
    by_key: dict[str, str] = {}
    for alias in aliases:
        by_key.setdefault(name_key(alias), alias)
    return by_key


def _check_names_are_free(
    session: Session, subject_id: UUID, concept_id: UUID, key: str, alias_keys: set[str]
) -> None:
    """The concept's name and aliases clash with nothing else in the subject.

    Name against name and alias against alias are also guarded by unique indexes; these checks
    cover the two mixed cases and the concept's own alias against its own name.
    """
    if key in alias_keys:
        raise Conflict(
            "An alias cannot be the same as the concept's own name.", code="DUPLICATE_NAME"
        )
    taken_as_name = (
        session.scalar(
            select(
                exists().where(
                    Concept.subject_id == subject_id,
                    Concept.id != concept_id,
                    Concept.name_key.in_(alias_keys),
                )
            )
        )
        if alias_keys
        else False
    )
    if taken_as_name:
        raise Conflict(
            "An alias is already the name of another concept in this subject.",
            code="DUPLICATE_NAME",
        )
    taken_as_alias = session.scalar(
        select(
            exists().where(
                ConceptAlias.subject_id == subject_id,
                ConceptAlias.concept_id != concept_id,
                ConceptAlias.alias_key == key,
            )
        )
    )
    if taken_as_alias:
        raise Conflict(
            "This name is already an alias of another concept in this subject.",
            code="DUPLICATE_NAME",
        )


def _replace_labels(session: Session, concept: Concept, labels: dict[str, str]) -> None:
    session.execute(
        delete(ConceptLabel).where(
            ConceptLabel.concept_id == concept.id, ConceptLabel.language.not_in(list(labels))
        )
    )
    for language, label in labels.items():
        existing = session.get(ConceptLabel, (concept.id, language))
        if existing is None:
            session.add(
                ConceptLabel(
                    organization_id=concept.organization_id,
                    concept_id=concept.id,
                    language=language,
                    label=label,
                )
            )
        else:
            existing.label = label


def _replace_aliases(session: Session, concept: Concept, aliases: dict[str, str]) -> None:
    session.execute(
        delete(ConceptAlias).where(
            ConceptAlias.concept_id == concept.id, ConceptAlias.alias_key.not_in(list(aliases))
        )
    )
    for key, alias in aliases.items():
        existing = session.get(ConceptAlias, (concept.id, key))
        if existing is None:
            session.add(
                ConceptAlias(
                    organization_id=concept.organization_id,
                    concept_id=concept.id,
                    subject_id=concept.subject_id,
                    alias=alias,
                    alias_key=key,
                )
            )
        else:
            existing.alias = alias


def create_concept(
    session: Session,
    principal: Principal,
    body: CreateConcept,
    *,
    idempotency_key: str | None,
    request_id: str | None,
) -> Concept:
    """Add a concept. A retry with the ``idempotency_key`` of an earlier, identical request returns
    that concept instead of failing with ``DUPLICATE_NAME`` because the first attempt worked."""
    require(principal, Action.MANAGE_CATALOGUES)
    organization_id = _organization_id(principal)
    concept_id = new_id()
    if idempotency_key is not None:
        concept_id = claim(
            session,
            actor_user_id=principal.user_id,
            operation="create_concept",
            key=idempotency_key,
            # The coaching is part of the request: a platform admin's key never reaches into
            # another coaching they acted in.
            body={**body.model_dump(mode="json"), "organization_id": str(organization_id)},
            new_resource_id=concept_id,
        )
        existing = session.get(Concept, concept_id)
        if existing is not None:
            return existing
    subject = _lock_subject(session, body.subject_id)
    if subject.kind != "SUBJECT":
        raise ValidationFailed(
            f"A concept belongs under a subject, not a {subject.kind.lower()}.",
            code="HIERARCHY_INVALID",
        )
    if subject.state != "ACTIVE":
        raise Conflict("The subject is retired.", code="PARENT_DEPRECATED")
    key = name_key(body.name)
    aliases = _unique_aliases(body.aliases)
    _check_names_are_free(session, subject.id, concept_id, key, set(aliases))
    concept = Concept(
        id=concept_id,
        organization_id=organization_id,
        subject_id=subject.id,
        name=body.name,
        name_key=key,
    )
    session.add(concept)
    _save(session)
    _replace_labels(session, concept, body.labels)
    _replace_aliases(session, concept, aliases)
    _save(session)
    record_event(
        session,
        action="CONCEPT_CREATED",
        entity_type="concept",
        entity_id=concept.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_acting(principal),
        request_id=request_id,
        after=_snapshot(session, concept),
    )
    return concept


def _locked_concept(session: Session, concept_id: UUID) -> Concept:
    """The concept, locked after its subject (the order every writer uses)."""
    concept = get_concept(session, concept_id)
    _lock_subject(session, concept.subject_id)
    locked = session.scalars(
        select(Concept).where(Concept.id == concept_id).with_for_update()
    ).first()
    if locked is None:
        raise NotFound("No such concept.")
    return locked


def _finish_change(
    session: Session,
    principal: Principal,
    concept: Concept,
    action: str,
    before: dict[str, Any],
    request_id: str | None,
) -> None:
    concept.revision += 1
    concept.updated_at = datetime.now(UTC)
    _save(session)
    record_event(
        session,
        action=action,
        entity_type="concept",
        entity_id=concept.id,
        organization_id=concept.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_acting(principal),
        request_id=request_id,
        before=before,
        after=_snapshot(session, concept),
    )


def update_concept(
    session: Session,
    principal: Principal,
    concept_id: UUID,
    body: UpdateConcept,
    *,
    if_match: str | None,
    request_id: str | None,
) -> Concept:
    """Rename, retranslate or change the aliases, refusing stale changes (If-Match).

    A change that changes nothing keeps the revision and writes no audit event.
    """
    require(principal, Action.MANAGE_CATALOGUES)
    concept = _locked_concept(session, concept_id)
    require_if_match(if_match, concept.revision)
    before = _snapshot(session, concept)
    if body.name is not None:
        concept.name = body.name
        concept.name_key = name_key(body.name)
        _save(
            session
        )  # before any query, so a name clash surfaces as the 409 and not as a raw error
    aliases = _unique_aliases(body.aliases) if body.aliases is not None else None
    final_alias_keys = (
        set(aliases)
        if aliases is not None
        else set(
            session.scalars(
                select(ConceptAlias.alias_key).where(ConceptAlias.concept_id == concept.id)
            )
        )
    )
    _check_names_are_free(
        session, concept.subject_id, concept.id, concept.name_key, final_alias_keys
    )
    if body.labels is not None:
        _replace_labels(session, concept, body.labels)
    if aliases is not None:
        _replace_aliases(session, concept, aliases)
    _save(session)  # before any query, so a name clash surfaces as the 409 and not as a raw error
    if _snapshot(session, concept) != before:
        _finish_change(session, principal, concept, "CONCEPT_UPDATED", before, request_id)
    return concept


def set_state(
    session: Session,
    principal: Principal,
    concept_id: UUID,
    state: str,
    *,
    if_match: str | None,
    request_id: str | None,
) -> Concept:
    """Retire or restore a concept. Asking for the state it already has changes nothing.

    Restoring is refused while its subject is retired.
    """
    require(principal, Action.MANAGE_CATALOGUES)
    concept = _locked_concept(session, concept_id)
    require_if_match(if_match, concept.revision)
    if concept.state == state:
        return concept
    if state == "ACTIVE":
        subject = _lock_subject(session, concept.subject_id)
        if subject.state != "ACTIVE":
            raise Conflict("Restore the subject first.", code="PARENT_DEPRECATED")
    before = _snapshot(session, concept)
    concept.state = state
    action = "CONCEPT_DEPRECATED" if state == "DEPRECATED" else "CONCEPT_RESTORED"
    _finish_change(session, principal, concept, action, before, request_id)
    return concept
