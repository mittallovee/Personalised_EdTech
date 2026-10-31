"""Starting and reading questions (M3 design note §5.1 and §6).

A question is a master (its permanent code), a version and revisions of the content. Saving a draft
with gaps is normal, so a save with findings is not an error; only unreadable or oversize content is
refused. Findings are computed from the content on every read and never stored.
"""

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.codes import normalize_code, reserve_code
from qbank.core.errors import NotFound, ValidationFailed
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.core.permissions import Action, may_access_draft, require
from qbank.modules.audit.public import record_event
from qbank.modules.questions.findings import Finding
from qbank.modules.questions.models import QuestionMaster, QuestionRevision, QuestionVersion
from qbank.modules.questions.rules import DEFAULT_RULES, Rules
from qbank.modules.questions.validate import validate_content

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


def _open(
    session: Session,
    principal: Principal,
    master: QuestionMaster | None,
    rules: Rules = DEFAULT_RULES,
) -> QuestionView:
    # Row-level security already hides other coachings' questions. Someone else's draft is also
    # "not found", so its existence is not given away.
    if master is None or not may_access_draft(principal, master.created_by):
        raise NotFound("No such question.")
    return _load(session, master, rules)


def _load(session: Session, master: QuestionMaster, rules: Rules = DEFAULT_RULES) -> QuestionView:
    version, revision = session.execute(
        select(QuestionVersion, QuestionRevision)
        .join(QuestionRevision, QuestionRevision.version_id == QuestionVersion.id)
        .where(QuestionVersion.master_id == master.id, QuestionRevision.frozen_at.is_(None))
        .order_by(QuestionVersion.number.desc())
        .limit(1)
    ).one()
    return QuestionView(master, version, revision, validate_content(revision.content, rules))
