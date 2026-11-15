"""Starting and reading questions (M3 design note §5.1 and §6).

A question is a master (its permanent code), a version and revisions of the content. Saving a draft
with gaps is normal, so a save with findings is not an error; only unreadable or oversize content is
refused. Findings are computed from the content on every read and never stored.
"""

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import Session, aliased

from qbank.core.auth import Principal
from qbank.core.codes import normalize_code, reserve_code
from qbank.core.errors import Conflict, NotFound, PermissionDenied, ValidationFailed
from qbank.core.etag import require_flow_if_match, require_if_match
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.core.permissions import (
    Action,
    is_allowed,
    may_access_all_drafts,
    may_access_draft,
    may_archive_draft,
    require,
)
from qbank.modules.assets.public import existing_image_ids
from qbank.modules.audit.public import record_event
from qbank.modules.questions.catalogue_checks import catalogue_ids, check_catalogue
from qbank.modules.questions.context_checks import check_pin, passage_pin
from qbank.modules.questions.domain.workflow import (
    EDITABLE_STATES,
    PRIVATE_STATES,
    ReturnReason,
    State,
    Step,
    Transition,
    allowed_steps,
    find_transition,
)
from qbank.modules.questions.domain.workflow_access import may_take_step
from qbank.modules.questions.findings import Finding, Level
from qbank.modules.questions.image_checks import check_images, image_ids
from qbank.modules.questions.limits import effective_rules, exam_of
from qbank.modules.questions.models import (
    QuestionMaster,
    QuestionRevision,
    QuestionVersion,
    ReviewDecision,
    RevisionAsset,
)
from qbank.modules.questions.passage_lookup import checkpoint_ids
from qbank.modules.questions.picture_records import record_pictures
from qbank.modules.questions.rules import DEFAULT_RULES, Rules
from qbank.modules.questions.settings_service import load_overrides
from qbank.modules.questions.validate import validate_content
from qbank.modules.taxonomy.public import look_up

ENTITY_TYPE = "question"

_PRIVATE = frozenset(state.value for state in PRIVATE_STATES)
_EDITABLE = frozenset(state.value for state in EDITABLE_STATES)


@dataclass(frozen=True, slots=True)
class QuestionView:
    """A question as read: its master, current version, working revision and the findings.

    While a version is in review, ``review_revision`` is the frozen revision the reviewers act on;
    what is shown and the findings are those of that revision, never of a working copy.
    """

    master: QuestionMaster
    version: QuestionVersion
    revision: QuestionRevision
    findings: list[Finding]
    review_revision: QuestionRevision | None = None

    @property
    def shown(self) -> QuestionRevision:
        return self.review_revision or self.revision


def _organization_id(principal: Principal) -> UUID:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise NotFound("No such question.")
    return organization_id


def check_storable(content: dict[str, Any], rules: Rules) -> None:
    """Refuse content that cannot be stored; gaps and mistakes inside it are findings, not this."""
    try:
        size = len(json.dumps(content, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except TypeError, ValueError:
        raise ValidationFailed(
            "The question has a value that is not plain data.", code="CONTENT_NOT_JSON"
        ) from None
    if size > rules.revision_bytes:
        raise ValidationFailed(
            f"This question is {size // 1024} KB; the limit is {rules.revision_bytes // 1024} KB.",
            code="CONTENT_TOO_LARGE",
        )


def create_question(
    session: Session,
    principal: Principal,
    content: dict[str, Any],
    *,
    idempotency_key: str | None,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """Start a question: a new code, version 1 and a working revision holding ``content``.

    A retry with the ``idempotency_key`` of an earlier identical request returns that question.
    """
    require(principal, Action.CREATE_QUESTIONS)
    organization_id = _organization_id(principal)
    check_storable(content, rules)
    master_id = new_id()
    if idempotency_key is not None:
        master_id = claim(
            session,
            actor_user_id=principal.user_id,
            operation="create_question",
            key=idempotency_key,
            # The coaching is part of the request: a platform admin's key never reaches into
            # another coaching they acted in.
            body={"content": content, "organization_id": str(organization_id)},
            new_resource_id=master_id,
        )
        existing = session.get(QuestionMaster, master_id)
        if existing is not None:
            return _load(session, existing, rules)

    master = QuestionMaster(
        id=master_id,
        organization_id=organization_id,
        code=reserve_code(session, entity_type=ENTITY_TYPE, organization_id=organization_id),
        created_by=principal.user_id,
    )
    version = QuestionVersion(
        id=new_id(), organization_id=organization_id, master_id=master.id, number=1
    )
    revision = QuestionRevision(
        organization_id=organization_id,
        version_id=version.id,
        number=1,
        content=content,
        author_id=principal.user_id,
    )
    # No ORM relationships tie these together, so each row is written before the next refers to it.
    for row in (master, version, revision):
        session.add(row)
        session.flush()
    _record_pictures(session, revision)
    question_type = content.get("question_type")
    record_event(
        session,
        action="QUESTION_CREATED",
        entity_type=ENTITY_TYPE,
        entity_id=master.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        after={
            "code": master.code,
            "question_type": question_type if isinstance(question_type, str) else None,
        },
    )
    return _load(session, master, rules)


def get_question(
    session: Session, principal: Principal, question_id: UUID, rules: Rules = DEFAULT_RULES
) -> QuestionView:
    return _open(session, principal, session.get(QuestionMaster, question_id), rules)


def get_question_by_code(
    session: Session, principal: Principal, typed_code: str, rules: Rules = DEFAULT_RULES
) -> QuestionView:
    """Find a question by the code a person typed (lower case and dashes are forgiven)."""
    master = session.scalars(
        select(QuestionMaster).where(QuestionMaster.code == normalize_code(typed_code))
    ).first()
    return _open(session, principal, master, rules)


def _findings_for(
    session: Session, contents: list[dict[str, Any]], rules: Rules
) -> list[list[Finding]]:
    """The findings of each content: its shape and parts, then its labels against this coaching's
    lists, then its pictures and the passage it sits under against this coaching's own. One lookup
    of each kind serves all of them, so a page of questions costs a handful of queries, not many."""
    ids = set[UUID]().union(*(catalogue_ids(content) for content in contents))
    refs = look_up(session, ids)
    pictures = existing_image_ids(session, set[UUID]().union(*(image_ids(c) for c in contents)))
    pins = {pin for pin in (passage_pin(c) for c in contents) if pin is not None}
    checkpoints = checkpoint_ids(session, pins)
    # The coaching's answer limits, and an exam's on top, apply to each question (D-03).
    overrides = load_overrides(session)
    return [
        validate_content(c, effective_rules(rules, overrides, exam_of(c)))
        + check_catalogue(c, refs)
        + check_images(c, pictures)
        + check_pin(c, checkpoints)
        for c in contents
    ]


def _record_pictures(session: Session, revision: QuestionRevision) -> None:
    record_pictures(
        session,
        RevisionAsset,
        organization_id=revision.organization_id,
        revision_id=revision.id,
        content=revision.content,
    )


def _findings(session: Session, content: dict[str, Any], rules: Rules) -> list[Finding]:
    return _findings_for(session, [content], rules)[0]


def _visible(principal: Principal, master: QuestionMaster | None) -> QuestionMaster:
    # Row-level security already hides other coachings' questions. Someone else's draft is also
    # "not found", so its existence is not given away.
    if master is None or not may_access_draft(principal, master.created_by):
        raise NotFound("No such question.")
    return master


def _open(
    session: Session,
    principal: Principal,
    master: QuestionMaster | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """Open one question. From submit on, every member may read it (M4 section 5); work in
    progress (a draft or a returned question) stays with its author, admins and the edit-others
    grant, and to anyone else it is "not found"."""
    if master is None or not is_allowed(principal, Action.CREATE_QUESTIONS):
        raise NotFound("No such question.")
    return _load(
        session, master, rules, include_private=may_access_draft(principal, master.created_by)
    )


def _load(
    session: Session,
    master: QuestionMaster,
    rules: Rules = DEFAULT_RULES,
    *,
    include_private: bool = True,
) -> QuestionView:
    query = (
        select(QuestionVersion, QuestionRevision)
        .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
        .where(QuestionVersion.master_id == master.id, QuestionRevision.frozen_at.is_(None))
        .order_by(QuestionVersion.number.desc())
        .limit(1)
    )
    if not include_private:
        query = query.where(QuestionVersion.state.not_in(_PRIVATE))
    row = session.execute(query).first()
    if row is None:
        raise NotFound("No such question.")
    version, revision = row
    reviewed = (
        session.get(QuestionRevision, version.review_revision_id)
        if version.review_revision_id is not None
        else None
    )
    findings = _findings(session, (reviewed or revision).content, rules)
    return QuestionView(master, version, revision, findings, reviewed)


def list_questions(
    session: Session,
    principal: Principal,
    *,
    mine_only: bool,
    archived: bool = False,
    limit: int,
    after: tuple[datetime, UUID] | None,
    rules: Rules = DEFAULT_RULES,
) -> tuple[list[QuestionView], bool]:
    """The questions the caller may open, newest first, after ``after`` (a cursor).

    Admins and holders of ``EDIT_OTHERS`` see every draft in the coaching unless ``mine_only``;
    everyone else sees their own. Archived questions are listed only when ``archived`` is true,
    and then only those. Returns the page and whether more follow.
    """
    require(principal, Action.CREATE_QUESTIONS)
    other = aliased(QuestionVersion)
    latest = (
        select(func.max(other.number)).where(other.master_id == QuestionMaster.id).scalar_subquery()
    )
    query = (
        select(QuestionMaster, QuestionVersion, QuestionRevision)
        .join(QuestionVersion, QuestionVersion.master_id == QuestionMaster.id)
        .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
        .where(QuestionRevision.frozen_at.is_(None), QuestionVersion.number == latest)
        .order_by(QuestionMaster.created_at.desc(), QuestionMaster.id.desc())
    )
    query = query.where(
        QuestionMaster.archived_at.is_not(None)
        if archived
        else QuestionMaster.archived_at.is_(None)
    )
    if mine_only or not may_access_all_drafts(principal):
        query = query.where(QuestionMaster.created_by == principal.user_id)
    if after is not None:
        query = query.where(tuple_(QuestionMaster.created_at, QuestionMaster.id) < after)
    rows = session.execute(query.limit(limit + 1)).all()
    page = rows[:limit]
    findings = _findings_for(session, [revision.content for _, _, revision in page], rules)
    views = [
        QuestionView(master, version, revision, found)
        for (master, version, revision), found in zip(page, findings, strict=True)
    ]
    return views, len(rows) > limit


# --- Changing the working revision -----------------------------------------------------------


def _lock(
    session: Session, principal: Principal, question_id: UUID
) -> tuple[QuestionMaster, QuestionVersion, QuestionRevision]:
    """The question, its newest version and that version's working revision, locked so two
    changes (saves or workflow steps) cannot interleave: every writer locks the master first.

    Work in progress that is someone else's is "not found"; submitted work is readable by every
    member. An archived question cannot be changed.
    """
    master = session.scalars(
        select(QuestionMaster).where(QuestionMaster.id == question_id).with_for_update()
    ).first()
    if master is None or not is_allowed(principal, Action.CREATE_QUESTIONS):
        raise NotFound("No such question.")
    version, revision = session.execute(
        select(QuestionVersion, QuestionRevision)
        .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
        .where(QuestionVersion.master_id == master.id, QuestionRevision.frozen_at.is_(None))
        .order_by(QuestionVersion.number.desc())
        .limit(1)
        .with_for_update(of=QuestionRevision)
    ).one()
    if version.state in _PRIVATE and not may_access_draft(principal, master.created_by):
        raise NotFound("No such question.")
    if master.archived_at is not None:
        raise Conflict(
            "This question is archived. Restore it to change it.", code="QUESTION_ARCHIVED"
        )
    return master, version, revision


def _lock_for_change(
    session: Session, principal: Principal, question_id: UUID
) -> tuple[QuestionMaster, QuestionVersion, QuestionRevision]:
    """``_lock`` for a change to the content: only editable work in progress may be saved."""
    master, version, revision = _lock(session, principal, question_id)
    if not may_access_draft(principal, master.created_by):
        raise NotFound("No such question.")
    if version.state not in _EDITABLE:
        raise Conflict(
            "This question is in review or published, so it cannot be edited. Withdraw it first.",
            code="QUESTION_NOT_EDITABLE",
            details={"state": version.state},
        )
    return master, version, revision


def save_working_revision(
    session: Session,
    principal: Principal,
    question_id: UUID,
    content: dict[str, Any],
    *,
    if_match: str | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """Autosave: replace the working revision's content in place (not audited: it would bury the
    log; the revision row records who saved last and when). ``if_match`` must be the ETag last read,
    or the save is refused (412) and nothing is overwritten."""
    require(principal, Action.CREATE_QUESTIONS)
    master, version, revision = _lock_for_change(session, principal, question_id)
    require_if_match(if_match, revision.revision)
    check_storable(content, rules)
    revision.content = content
    revision.author_id = principal.user_id
    revision.revision += 1
    revision.updated_at = datetime.now(UTC)
    session.flush()
    _record_pictures(session, revision)
    return QuestionView(master, version, revision, _findings(session, content, rules))


def content_hash(content: dict[str, Any]) -> str:
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _freeze_working(
    session: Session,
    principal: Principal,
    master: QuestionMaster,
    version: QuestionVersion,
    revision: QuestionRevision,
) -> QuestionRevision:
    """Freeze the working revision (with a hash of its content) and start a new working revision
    as a copy of it. Returns the new one; its ETag continues the old one's count, so a tab that
    still holds the old ETag can never match it."""
    revision.content_hash = content_hash(revision.content)
    revision.frozen_at = datetime.now(UTC)
    session.flush()  # frozen first: a version has only one working revision at a time
    fresh = QuestionRevision(
        id=new_id(),
        organization_id=master.organization_id,
        version_id=version.id,
        number=revision.number + 1,
        content=copy.deepcopy(revision.content),
        author_id=principal.user_id,
        revision=revision.revision + 1,
    )
    session.add(fresh)
    session.flush()
    _record_pictures(session, fresh)
    return fresh


def checkpoint(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> tuple[QuestionView, int]:
    """Freeze the working revision (with a hash of its content) and start a new one as a copy.

    Returns the new working revision and the number of the frozen one. The new revision's ETag
    continues the old one's count, so a tab that still holds the old ETag can never match it.
    """
    require(principal, Action.CREATE_QUESTIONS)
    master, version, revision = _lock_for_change(session, principal, question_id)
    require_if_match(if_match, revision.revision)
    fresh = _freeze_working(session, principal, master, version, revision)
    record_event(
        session,
        action="QUESTION_CHECKPOINTED",
        entity_type=ENTITY_TYPE,
        entity_id=master.id,
        organization_id=master.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        after={"code": master.code, "revision_number": revision.number},
    )
    view = QuestionView(master, version, fresh, _findings(session, fresh.content, rules))
    return view, revision.number


# --- Workflow steps (M4 design note section 4, ADR-0020) ---------------------------------------


def steps_for(principal: Principal, view: QuestionView) -> list[Step]:
    """The steps this person may take now. The web shows exactly these and holds no rules."""
    if view.master.archived_at is not None:
        return []
    state = State(view.version.state)
    return [
        step
        for step in allowed_steps(state)
        if may_take_step(principal, state, step, author_id=view.master.created_by)
    ]


def _require_step(
    principal: Principal, master: QuestionMaster, version: QuestionVersion, step: Step
) -> Transition:
    """The transition if the version's state allows the step and this person may take it.

    The caller has already checked ``If-Match``, so a person who read an older state hears
    "changed, reload" (412) before anything else. After that, the state is told first (409):
    anyone who got this far may read the question, so it gives nothing away. A step the person
    may not take is 403.
    """
    state = State(version.state)
    transition = find_transition(state, step)
    if transition is None:
        raise Conflict(
            f"A question that is {state.value.lower().replace('_', ' ')} cannot take that step.",
            code="WORKFLOW_STEP_INVALID",
            details={"state": state.value, "allowed": [s.value for s in allowed_steps(state)]},
        )
    if not may_take_step(principal, state, step, author_id=master.created_by):
        raise PermissionDenied("You don't have permission to do this.")
    return transition


def _move(
    session: Session,
    principal: Principal,
    master: QuestionMaster,
    version: QuestionVersion,
    transition: Transition,
    *,
    revision_id: UUID,
    review_revision_id: UUID | None,
    audit_action: str,
    request_id: str | None,
    reasons: list[str] | None = None,
    note: str | None = None,
    checklist: dict[str, Any] | None = None,
) -> None:
    """Take the step: change the state, raise the workflow ETag, and write the decision and the
    audit event in the same transaction. The database trigger checks the pair again.

    ``reasons`` and ``note`` belong to a return; ``checklist`` is the evidence kept for a step that
    needed the publication checklist."""
    from_state = version.state
    version.state = transition.result.value
    version.flow_revision += 1
    version.review_revision_id = review_revision_id
    version.state_changed_at = datetime.now(UTC)
    session.flush()
    session.add(
        ReviewDecision(
            organization_id=master.organization_id,
            version_id=version.id,
            revision_id=revision_id,
            step=transition.step.value,
            from_state=from_state,
            to_state=version.state,
            flow_revision=version.flow_revision,
            actor_id=principal.user_id,
            reasons=reasons or [],
            note=note,
            checklist=checklist,
        )
    )
    session.flush()
    record_event(
        session,
        action=audit_action,
        entity_type=ENTITY_TYPE,
        entity_id=master.id,
        organization_id=master.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before={"state": from_state},
        after={
            "code": master.code,
            "state": version.state,
            "version_number": version.number,
            "revision_id": str(revision_id),
            **({"reasons": reasons} if reasons else {}),
        },
    )


def submit(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """Send the working revision for review (E-01).

    It is frozen as the review revision; reviewers act on that text, never on a working copy, and
    the editor stays read-only until a withdraw. Gaps ("still to do") are allowed; mistakes
    (``error`` findings) are not. ``if_match`` is the working revision's ETag, as for a checkpoint.
    """
    require(principal, Action.CREATE_QUESTIONS)
    master, version, working = _lock(session, principal, question_id)
    require_if_match(if_match, working.revision)
    transition = _require_step(principal, master, version, Step.SUBMIT)
    found = _findings(session, working.content, rules)
    errors = [f for f in found if f.level == Level.ERROR]
    if errors:
        raise ValidationFailed(
            "Fix the mistakes in this question before sending it for review.",
            code="QUESTION_HAS_ERRORS",
            details={
                "findings": [
                    {"path": f.path, "code": f.code, "level": f.level.value, "message": f.message}
                    for f in errors
                ]
            },
        )
    fresh = _freeze_working(session, principal, master, version, working)
    _move(
        session,
        principal,
        master,
        version,
        transition,
        revision_id=working.id,
        review_revision_id=working.id,
        audit_action="QUESTION_SUBMITTED",
        request_id=request_id,
    )
    return QuestionView(master, version, fresh, found, working)


def withdraw(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """Take a question back from review so it can be edited again (decision 2). The decisions
    so far stay in the history. ``if_match`` is the workflow ETag (``"flow-N"``)."""
    require(principal, Action.CREATE_QUESTIONS)
    master, version, working = _lock(session, principal, question_id)
    require_flow_if_match(if_match, version.flow_revision)
    transition = _require_step(principal, master, version, Step.WITHDRAW)
    reviewed = version.review_revision_id
    if reviewed is None:  # the database already guarantees this for a state that can be withdrawn
        raise Conflict("This question has nothing under review.", code="WORKFLOW_STEP_INVALID")
    _move(
        session,
        principal,
        master,
        version,
        transition,
        revision_id=reviewed,
        review_revision_id=None,
        audit_action="QUESTION_WITHDRAWN",
        request_id=request_id,
    )
    return QuestionView(master, version, working, _findings(session, working.content, rules))


# --- History ---------------------------------------------------------------------------------


def list_revisions(
    session: Session, principal: Principal, question_id: UUID
) -> tuple[QuestionMaster, list[tuple[QuestionVersion, QuestionRevision]]]:
    """Every saved revision, newest first (the working one on top)."""
    master = _visible(principal, session.get(QuestionMaster, question_id))
    rows = session.execute(
        select(QuestionVersion, QuestionRevision)
        .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
        .where(QuestionVersion.master_id == master.id)
        .order_by(QuestionVersion.number.desc(), QuestionRevision.number.desc())
    ).all()
    return master, [(version, revision) for version, revision in rows]


def get_revision(
    session: Session,
    principal: Principal,
    question_id: UUID,
    number: int,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """One revision of the question's current version, read-only, with findings as of now."""
    master = _visible(principal, session.get(QuestionMaster, question_id))
    other = aliased(QuestionVersion)
    latest = select(func.max(other.number)).where(other.master_id == master.id).scalar_subquery()
    row = session.execute(
        select(QuestionVersion, QuestionRevision)
        .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
        .where(
            QuestionVersion.master_id == master.id,
            QuestionRevision.number == number,
            QuestionVersion.number == latest,
        )
    ).first()
    if row is None:
        raise NotFound("No such revision.")
    version, revision = row
    return QuestionView(master, version, revision, _findings(session, revision.content, rules))


def set_archived(
    session: Session,
    principal: Principal,
    question_id: UUID,
    archived: bool,
    *,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """Archive or restore a question. Nothing is deleted and the code stays reserved. Doing it
    twice changes and audits nothing. Someone who may open the draft but not archive it is
    refused (403); someone who may not open it gets "not found"."""
    require(principal, Action.CREATE_QUESTIONS)
    master = _visible(
        principal,
        session.scalars(
            select(QuestionMaster).where(QuestionMaster.id == question_id).with_for_update()
        ).first(),
    )
    if not may_archive_draft(principal, master.created_by):
        raise PermissionDenied("Only the author or an admin can archive or restore a question.")
    if (master.archived_at is not None) != archived:
        master.archived_at = datetime.now(UTC) if archived else None
        master.revision += 1
        session.flush()
        record_event(
            session,
            action="QUESTION_ARCHIVED" if archived else "QUESTION_RESTORED",
            entity_type=ENTITY_TYPE,
            entity_id=master.id,
            organization_id=master.organization_id,
            actor_user_id=principal.user_id,
            actor_is_platform=principal.acting_organization_id is not None,
            request_id=request_id,
            after={"code": master.code},
        )
    return _load(session, master, rules)


# --- Return, pass QC and approve (M4 design note 4.3 and 4.4) ----------------------------------


MIN_NOTE = 10  # characters, after the spaces around it are removed (design note 4.3)
_BLOCKING = frozenset({Level.ERROR, Level.INCOMPLETE})


def _under_review(session: Session, version: QuestionVersion) -> QuestionRevision:
    reviewed = (
        session.get(QuestionRevision, version.review_revision_id)
        if version.review_revision_id is not None
        else None
    )
    if reviewed is None:  # the database already guarantees this for a state that is under review
        raise Conflict("This question has nothing under review.", code="WORKFLOW_STEP_INVALID")
    return reviewed


def _publication_checklist(
    session: Session, reviewed: QuestionRevision, rules: Rules
) -> tuple[list[Finding], dict[str, Any]]:
    """The checklist (E-07) is the findings engine run on the frozen review revision, against the
    coaching's catalogue and answer limits as they are now. Anything that is an ``error`` or still
    to do blocks; a warning does not. Returns all the findings and the evidence to keep."""
    found = _findings(session, reviewed.content, rules)
    blocking = [f for f in found if f.level in _BLOCKING]
    if blocking:
        raise ValidationFailed(
            "This question does not meet the publication checklist yet.",
            code="PUBLICATION_CHECKLIST_FAILED",
            details={
                "findings": [
                    {"path": f.path, "code": f.code, "level": f.level.value, "message": f.message}
                    for f in blocking
                ]
            },
        )
    warnings = [f.code for f in found if f.level == Level.WARNING]
    return found, {"passed": True, "warnings": warnings}


def _checked_step(
    session: Session,
    principal: Principal,
    question_id: UUID,
    step: Step,
    *,
    if_match: str | None,
    request_id: str | None,
    audit_action: str,
    rules: Rules,
) -> QuestionView:
    """Pass QC or approve: the same frozen revision moves on, but only with a complete checklist."""
    require(principal, Action.CREATE_QUESTIONS)
    master, version, working = _lock(session, principal, question_id)
    require_flow_if_match(if_match, version.flow_revision)
    transition = _require_step(principal, master, version, step)
    reviewed = _under_review(session, version)
    found, checklist = _publication_checklist(session, reviewed, rules)
    _move(
        session,
        principal,
        master,
        version,
        transition,
        revision_id=reviewed.id,
        review_revision_id=reviewed.id,
        audit_action=audit_action,
        request_id=request_id,
        checklist=checklist,
    )
    return QuestionView(master, version, working, found, reviewed)


def pass_qc(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """Quality control passes the frozen revision (E-01, E-07). ``if_match`` is ``"flow-N"``."""
    return _checked_step(
        session,
        principal,
        question_id,
        Step.PASS_QC,
        if_match=if_match,
        request_id=request_id,
        audit_action="QUESTION_QC_PASSED",
        rules=rules,
    )


def approve(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """Approval of the revision QC passed; the checklist is checked again (E-07)."""
    return _checked_step(
        session,
        principal,
        question_id,
        Step.APPROVE,
        if_match=if_match,
        request_id=request_id,
        audit_action="QUESTION_APPROVED",
        rules=rules,
    )


def _clean_reasons(reasons: list[ReturnReason], note: str) -> tuple[list[str], str]:
    """The reasons (each once, in the order given) and the note without the spaces around it."""
    kept = list(dict.fromkeys(reason.value for reason in reasons))
    text = note.strip()
    if not kept or len(text) < MIN_NOTE:
        raise ValidationFailed(
            f"Choose at least one reason and write a note of at least {MIN_NOTE} characters.",
            code="RETURN_REASON_REQUIRED",
        )
    return kept, text


def return_question(
    session: Session,
    principal: Principal,
    question_id: UUID,
    *,
    reasons: list[ReturnReason],
    note: str,
    if_match: str | None,
    request_id: str | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    """Send a question back to its author with reasons and a note (E-06).

    It becomes the author's work in progress again, so the reply shows the revision that was
    returned, the text the reviewer had in front of them, not the author's working copy.
    """
    require(principal, Action.CREATE_QUESTIONS)
    master, version, working = _lock(session, principal, question_id)
    require_flow_if_match(if_match, version.flow_revision)
    transition = _require_step(principal, master, version, Step.RETURN)
    kept, text = _clean_reasons(reasons, note)
    reviewed = _under_review(session, version)
    _move(
        session,
        principal,
        master,
        version,
        transition,
        revision_id=reviewed.id,
        review_revision_id=None,
        audit_action="QUESTION_RETURNED",
        request_id=request_id,
        reasons=kept,
        note=text,
    )
    found = _findings(session, reviewed.content, rules)
    return QuestionView(master, version, working, found, reviewed)
