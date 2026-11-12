"""Starting, saving and reading passages (M3 design note §5.6, D-14).

A passage is shared text with a working revision that is saved in place (guarded by ``If-Match``)
and checkpoints that freeze it for good. A child question pins one frozen revision, so editing the
passage later never changes what a question was written under. Like a question, a draft with gaps
is saved; the findings are computed on every read and never stored.
"""

import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, case, cast, func, select, tuple_
from sqlalchemy.orm import Session, aliased

from qbank.core.auth import Principal
from qbank.core.errors import NotFound
from qbank.core.etag import require_if_match
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.core.permissions import Action, may_access_all_drafts, may_access_draft, require
from qbank.modules.assets.public import existing_image_ids
from qbank.modules.audit.public import record_event
from qbank.modules.questions.findings import Finding
from qbank.modules.questions.image_checks import check_images, image_ids
from qbank.modules.questions.models import (
    Passage,
    PassageRevision,
    PassageRevisionAsset,
    QuestionMaster,
    QuestionRevision,
    QuestionVersion,
)
from qbank.modules.questions.passage_content import empty_passage, validate_passage
from qbank.modules.questions.picture_records import record_pictures
from qbank.modules.questions.rules import DEFAULT_RULES, Rules
from qbank.modules.questions.service import check_storable, content_hash

ENTITY_TYPE = "passage"


@dataclass(frozen=True, slots=True)
class PassageView:
    """A passage as read: the passage, its working revision, its newest checkpoint and findings."""

    passage: Passage
    revision: PassageRevision
    latest_checkpoint: PassageRevision | None
    findings: list[Finding]


def _organization_id(principal: Principal) -> UUID:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise NotFound("No such passage.")
    return organization_id


def passage_findings(session: Session, content: dict[str, Any], rules: Rules) -> list[Finding]:
    """The shape of the passage, then its pictures against this coaching's own."""
    pictures = existing_image_ids(session, image_ids(content))
    return validate_passage(content, rules) + check_images(content, pictures)


def _record_pictures(session: Session, revision: PassageRevision) -> None:
    record_pictures(
        session,
        PassageRevisionAsset,
        organization_id=revision.organization_id,
        revision_id=revision.id,
        content=revision.content,
    )


def _latest_checkpoint(session: Session, passage_id: UUID) -> PassageRevision | None:
    return session.scalars(
        select(PassageRevision)
        .where(PassageRevision.passage_id == passage_id, PassageRevision.frozen_at.is_not(None))
        .order_by(PassageRevision.number.desc())
        .limit(1)
    ).first()


def _working(session: Session, passage_id: UUID, *, lock: bool = False) -> PassageRevision:
    query = select(PassageRevision).where(
        PassageRevision.passage_id == passage_id, PassageRevision.frozen_at.is_(None)
    )
    return session.scalars(query.with_for_update() if lock else query).one()


def _visible(principal: Principal, passage: Passage | None) -> Passage:
    # Row-level security already hides other coachings' passages. Someone else's draft is also
    # "not found", so its existence is not given away.
    if passage is None or not may_access_draft(principal, passage.created_by):
        raise NotFound("No such passage.")
    return passage


def _view(session: Session, passage: Passage, rules: Rules = DEFAULT_RULES) -> PassageView:
    revision = _working(session, passage.id)
    return PassageView(
        passage,
        revision,
        _latest_checkpoint(session, passage.id),
        passage_findings(session, revision.content, rules),
    )


def create_passage(
    session: Session,
    principal: Principal,
    content: dict[str, Any] | None,
    *,
    idempotency_key: str | None,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> PassageView:
    """Start a passage: working revision 1 holding ``content`` (an empty passage if none)."""
    require(principal, Action.CREATE_QUESTIONS)
    organization_id = _organization_id(principal)
    start = content if content is not None else empty_passage()
    check_storable(start, rules)
    passage_id = new_id()
    if idempotency_key is not None:
        passage_id = claim(
            session,
            actor_user_id=principal.user_id,
            operation="create_passage",
            key=idempotency_key,
            body={"content": start, "organization_id": str(organization_id)},
            new_resource_id=passage_id,
        )
        existing = session.get(Passage, passage_id)
        if existing is not None:
            return _view(session, existing, rules)
    passage = Passage(id=passage_id, organization_id=organization_id, created_by=principal.user_id)
    session.add(passage)
    session.flush()
    revision = PassageRevision(
        organization_id=organization_id,
        passage_id=passage.id,
        number=1,
        content=start,
        author_id=principal.user_id,
    )
    session.add(revision)
    session.flush()
    _record_pictures(session, revision)
    record_event(
        session,
        action="PASSAGE_CREATED",
        entity_type=ENTITY_TYPE,
        entity_id=passage.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
    )
    return _view(session, passage, rules)


def get_passage(
    session: Session, principal: Principal, passage_id: UUID, rules: Rules = DEFAULT_RULES
) -> PassageView:
    require(principal, Action.CREATE_QUESTIONS)
    return _view(session, _visible(principal, session.get(Passage, passage_id)), rules)


def list_passages(
    session: Session,
    principal: Principal,
    *,
    mine_only: bool,
    limit: int,
    after: tuple[datetime, UUID] | None,
) -> tuple[list[tuple[Passage, PassageRevision, int | None]], bool]:
    """The passages the caller may open, newest first, after ``after`` (a cursor).

    Each row is the passage, its working revision and the number of its newest checkpoint (or
    ``None``). Returns the page and whether more follow.
    """
    require(principal, Action.CREATE_QUESTIONS)
    newest = (
        select(func.max(PassageRevision.number))
        .where(PassageRevision.passage_id == Passage.id, PassageRevision.frozen_at.is_not(None))
        .correlate(Passage)
        .scalar_subquery()
    )
    query = (
        select(Passage, PassageRevision, newest)
        .join(PassageRevision, PassageRevision.passage_id == Passage.id)
        .where(PassageRevision.frozen_at.is_(None))
        .order_by(Passage.created_at.desc(), Passage.id.desc())
    )
    if mine_only or not may_access_all_drafts(principal):
        query = query.where(Passage.created_by == principal.user_id)
    if after is not None:
        query = query.where(tuple_(Passage.created_at, Passage.id) < after)
    rows = session.execute(query.limit(limit + 1)).all()
    page = [(passage, revision, number) for passage, revision, number in rows[:limit]]
    return page, len(rows) > limit


def _lock_for_change(
    session: Session, principal: Principal, passage_id: UUID
) -> tuple[Passage, PassageRevision]:
    passage = session.scalars(
        select(Passage).where(Passage.id == passage_id).with_for_update()
    ).first()
    passage = _visible(principal, passage)
    return passage, _working(session, passage.id, lock=True)


def save_working_revision(
    session: Session,
    principal: Principal,
    passage_id: UUID,
    content: dict[str, Any],
    *,
    if_match: str | None,
    rules: Rules = DEFAULT_RULES,
) -> PassageView:
    """Autosave: replace the working revision's content in place (not audited). ``if_match`` must
    be the ETag last read, or the save is refused (412) and nothing is overwritten."""
    require(principal, Action.CREATE_QUESTIONS)
    passage, revision = _lock_for_change(session, principal, passage_id)
    require_if_match(if_match, revision.revision)
    check_storable(content, rules)
    revision.content = content
    revision.author_id = principal.user_id
    revision.revision += 1
    revision.updated_at = datetime.now(UTC)
    session.flush()
    _record_pictures(session, revision)
    return PassageView(
        passage,
        revision,
        _latest_checkpoint(session, passage.id),
        passage_findings(session, content, rules),
    )


def checkpoint(
    session: Session,
    principal: Principal,
    passage_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> tuple[PassageView, PassageRevision]:
    """Freeze the working revision (with a hash of its content) and start a new one as a copy.

    Returns the new working revision's view and the frozen revision. The new revision's ETag
    continues the old one's count, so a tab that still holds the old ETag can never match it.
    """
    require(principal, Action.CREATE_QUESTIONS)
    passage, revision = _lock_for_change(session, principal, passage_id)
    require_if_match(if_match, revision.revision)
    revision.content_hash = content_hash(revision.content)
    revision.frozen_at = datetime.now(UTC)
    session.flush()  # frozen first: a passage has only one working revision at a time
    fresh = PassageRevision(
        id=new_id(),
        organization_id=passage.organization_id,
        passage_id=passage.id,
        number=revision.number + 1,
        content=copy.deepcopy(revision.content),
        author_id=principal.user_id,
        revision=revision.revision + 1,
    )
    session.add(fresh)
    session.flush()
    _record_pictures(session, fresh)
    record_event(
        session,
        action="PASSAGE_CHECKPOINTED",
        entity_type=ENTITY_TYPE,
        entity_id=passage.id,
        organization_id=passage.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        after={"revision_number": revision.number},
    )
    return PassageView(
        passage, fresh, revision, passage_findings(session, fresh.content, rules)
    ), revision


def list_revisions(
    session: Session, principal: Principal, passage_id: UUID
) -> list[PassageRevision]:
    """The passage's revisions, newest first (the working one, then the checkpoints)."""
    require(principal, Action.CREATE_QUESTIONS)
    passage = _visible(principal, session.get(Passage, passage_id))
    return list(
        session.scalars(
            select(PassageRevision)
            .where(PassageRevision.passage_id == passage.id)
            .order_by(PassageRevision.number.desc())
        )
    )


def get_checkpoint(
    session: Session, principal: Principal, revision_id: UUID, rules: Rules = DEFAULT_RULES
) -> tuple[PassageRevision, list[Finding]]:
    """A frozen revision, by its id: what a child question pins.

    Any member of the coaching may read a checkpoint, because the questions under it show it.
    The passage's working revision (a draft) is not served here.
    """
    require(principal, Action.CREATE_QUESTIONS)
    revision = session.get(PassageRevision, revision_id)
    if revision is None or revision.frozen_at is None:
        raise NotFound("No such passage revision.")
    return revision, passage_findings(session, revision.content, rules)


MAX_CHILDREN = 500


@dataclass(frozen=True, slots=True)
class PassageChild:
    """A question that sits under the passage, and which checkpoint it was written with."""

    master: QuestionMaster
    question_type: str | None
    ordinal: int | None
    pinned_number: int
    is_current: bool


@dataclass(frozen=True, slots=True)
class PassageChildren:
    children: list[PassageChild]
    latest_checkpoint_number: int | None
    hidden_count: int
    truncated: bool


def _ordinal(content: dict[str, Any]) -> int | None:
    context = content.get("context")
    value = context.get("ordinal") if isinstance(context, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def list_children(session: Session, principal: Principal, passage_id: UUID) -> PassageChildren:
    """The questions that pin a checkpoint of this passage, in the order of their numbers.

    Which children are on an older checkpoint than the newest is told per child. Children are
    questions, so someone else's draft is not shown to a caller who may not open it; they are
    counted in ``hidden_count`` instead. A list longer than ``MAX_CHILDREN`` is cut and says so
    (``truncated``), so it never looks complete when it is not.
    """
    require(principal, Action.CREATE_QUESTIONS)
    passage = _visible(principal, session.get(Passage, passage_id))
    checkpoints = {
        str(r.id): r.number
        for r in session.scalars(
            select(PassageRevision).where(
                PassageRevision.passage_id == passage.id, PassageRevision.frozen_at.is_not(None)
            )
        )
    }
    if not checkpoints:
        return PassageChildren([], None, 0, False)
    latest = max(checkpoints.values())
    other = aliased(QuestionVersion)
    newest = (
        select(func.max(other.number)).where(other.master_id == QuestionMaster.id).scalar_subquery()
    )
    pinned = QuestionRevision.content["context"]["passage_revision_id"].astext
    typed = QuestionRevision.content["context"]["ordinal"].astext
    # A number that is not a whole number sorts last; the test guards the cast, so it never fails.
    ordinal = case((typed.op("~")("^[0-9]{1,4}$"), cast(typed, Integer)), else_=None)
    under_this_passage = (
        QuestionRevision.frozen_at.is_(None),
        QuestionVersion.number == newest,
        pinned.in_(list(checkpoints)),
    )
    # What the caller may open is chosen here, not afterwards, so the limit below never fills up
    # with drafts that would be left out.
    opens_all = may_access_all_drafts(principal)
    mine_only = () if opens_all else (QuestionMaster.created_by == principal.user_id,)
    rows = session.execute(
        select(QuestionMaster, QuestionRevision)
        .join(QuestionVersion, QuestionVersion.master_id == QuestionMaster.id)
        .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
        .where(*under_this_passage, *mine_only)
        .order_by(ordinal.asc().nulls_last(), QuestionMaster.created_at, QuestionMaster.id)
        .limit(MAX_CHILDREN + 1)
    ).all()
    hidden = (
        0
        if opens_all
        else session.execute(
            select(func.count())
            .select_from(QuestionMaster)
            .join(QuestionVersion, QuestionVersion.master_id == QuestionMaster.id)
            .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
            .where(*under_this_passage, QuestionMaster.created_by != principal.user_id)
        ).scalar_one()
    )
    children: list[PassageChild] = []
    for master, revision in rows[:MAX_CHILDREN]:
        number = checkpoints[revision.content["context"]["passage_revision_id"]]
        question_type = revision.content.get("question_type")
        children.append(
            PassageChild(
                master,
                question_type if isinstance(question_type, str) else None,
                _ordinal(revision.content),
                number,
                number == latest,
            )
        )
    return PassageChildren(children, latest, hidden, len(rows) > MAX_CHILDREN)
