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
from qbank.core.etag import require_if_match
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.core.permissions import (
    Action,
    may_access_all_drafts,
    may_access_draft,
    may_archive_draft,
    require,
)
from qbank.modules.audit.public import record_event
from qbank.modules.questions.catalogue_checks import catalogue_ids, check_catalogue
from qbank.modules.questions.findings import Finding
from qbank.modules.questions.models import QuestionMaster, QuestionRevision, QuestionVersion
from qbank.modules.questions.rules import DEFAULT_RULES, Rules
from qbank.modules.questions.validate import validate_content
from qbank.modules.taxonomy.public import look_up

ENTITY_TYPE = "question"


@dataclass(frozen=True, slots=True)
class QuestionView:
    """A question as read: its master, current version, working revision and the findings."""

    master: QuestionMaster
    version: QuestionVersion
    revision: QuestionRevision
    findings: list[Finding]


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
    lists. One lookup serves all of them, so a page of questions costs four queries, not many."""
    ids = set[UUID]().union(*(catalogue_ids(content) for content in contents))
    refs = look_up(session, ids)
    return [validate_content(c, rules) + check_catalogue(c, refs) for c in contents]


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
    return _load(session, _visible(principal, master), rules)


def _load(session: Session, master: QuestionMaster, rules: Rules = DEFAULT_RULES) -> QuestionView:
    version, revision = session.execute(
        select(QuestionVersion, QuestionRevision)
        .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
        .where(QuestionVersion.master_id == master.id, QuestionRevision.frozen_at.is_(None))
        .order_by(QuestionVersion.number.desc())
        .limit(1)
    ).one()
    return QuestionView(master, version, revision, _findings(session, revision.content, rules))


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


def _lock_for_change(
    session: Session, principal: Principal, question_id: UUID
) -> tuple[QuestionMaster, QuestionVersion, QuestionRevision]:
    """The question and its working revision, locked so two saves cannot interleave.

    Someone else's draft is "not found". An archived question cannot be changed.
    """
    master = session.scalars(
        select(QuestionMaster).where(QuestionMaster.id == question_id).with_for_update()
    ).first()
    if master is None or not may_access_draft(principal, master.created_by):
        raise NotFound("No such question.")
    if master.archived_at is not None:
        raise Conflict(
            "This question is archived. Restore it to change it.", code="QUESTION_ARCHIVED"
        )
    version, revision = session.execute(
        select(QuestionVersion, QuestionRevision)
        .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
        .where(QuestionVersion.master_id == master.id, QuestionRevision.frozen_at.is_(None))
        .order_by(QuestionVersion.number.desc())
        .limit(1)
        .with_for_update(of=QuestionRevision)
    ).one()
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
    return QuestionView(master, version, revision, _findings(session, content, rules))


def content_hash(content: dict[str, Any]) -> str:
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


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
    now = datetime.now(UTC)
    revision.content_hash = content_hash(revision.content)
    revision.frozen_at = now
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
