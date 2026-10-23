"""Exams and sources (M3 design note §4.3): lists the admins keep and questions point at.

Both are a name that is unique within the coaching, and both are retired rather than deleted. The
logic is the same, so it is written once and described by a ``Catalogue``.
"""

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, MalformedRequest, NotFound
from qbank.core.etag import require_if_match
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.core.permissions import Action, require
from qbank.modules.audit.public import record_event
from qbank.modules.taxonomy.catalogues import name_key
from qbank.modules.taxonomy.models import Exam, Source


@dataclass(frozen=True, slots=True)
class Catalogue:
    model: Any  # the table class: Exam or Source
    noun: str  # for messages: "exam"
    entity_type: str  # for the audit log
    action_prefix: str  # audit actions: EXAM_CREATED, EXAM_UPDATED...
    fields: tuple[str, ...]  # the columns people edit, shown in audit snapshots
    unique_indexes: tuple[str, ...]  # a violation of these means "this name is taken"


EXAMS = Catalogue(
    model=Exam,
    noun="exam",
    entity_type="exam",
    action_prefix="EXAM",
    fields=("name", "short_code", "state"),
    unique_indexes=("exams_name",),
)
SOURCES = Catalogue(
    model=Source,
    noun="source",
    entity_type="source",
    action_prefix="SOURCE",
    fields=("kind", "name", "state"),
    unique_indexes=("sources_name",),
)


def _acting(principal: Principal) -> bool:
    return principal.acting_organization_id is not None


def _organization_id(principal: Principal) -> UUID:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise NotFound("No such item.")
    return organization_id


# --- Reading ----------------------------------------------------------------------------------


def next_cursor(items: list[Any], has_more: bool) -> str | None:
    if not (has_more and items):
        return None
    raw = json.dumps([items[-1].name_key, str(items[-1].id)]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[str, UUID]:
    """Inverse of ``next_cursor``; a damaged cursor is a 400, never a 500."""
    invalid = MalformedRequest("The page cursor is not valid. Start again from the first page.")
    try:
        data = json.loads(base64.urlsafe_b64decode((cursor + "=" * (-len(cursor) % 4)).encode()))
    except binascii.Error, UnicodeDecodeError, ValueError:
        raise invalid from None
    if not (
        isinstance(data, list)
        and len(data) == 2
        and isinstance(data[0], str)
        and isinstance(data[1], str)
    ):
        raise invalid
    try:
        return data[0], UUID(data[1])
    except ValueError:
        raise invalid from None


def list_items(
    session: Session,
    catalogue: Catalogue,
    *,
    state: str | None,
    limit: int,
    after: tuple[str, UUID] | None,
    where: tuple[ColumnElement[bool], ...] = (),
) -> tuple[list[Any], bool]:
    """In name order. Returns the page and whether more follow."""
    model = catalogue.model
    query = select(model).order_by(model.name_key, model.id)
    for condition in where:
        query = query.where(condition)
    if state is not None:
        query = query.where(model.state == state)
    if after is not None:
        key, item_id = after
        query = query.where(
            (model.name_key > key) | ((model.name_key == key) & (model.id > item_id))
        )
    rows = list(session.scalars(query.limit(limit + 1)))
    return rows[:limit], len(rows) > limit


def get_item(session: Session, catalogue: Catalogue, item_id: UUID) -> Any:
    item = session.get(catalogue.model, item_id)  # row-level security hides other coachings'
    if item is None:
        raise NotFound(f"No such {catalogue.noun}.")
    return item


# --- Changing ---------------------------------------------------------------------------------


def _snapshot(catalogue: Catalogue, item: Any) -> dict[str, Any]:
    return {field: getattr(item, field) for field in catalogue.fields}


def _save(session: Session, catalogue: Catalogue) -> None:
    """Flush, turning "this name is taken" into a clear 409."""
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as error:
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint in catalogue.unique_indexes:
            raise Conflict(
                f"Another {catalogue.noun} already has this name.", code="DUPLICATE_NAME"
            ) from None
        raise


def create_item(
    session: Session,
    principal: Principal,
    catalogue: Catalogue,
    values: dict[str, Any],
    *,
    idempotency_key: str | None,
    request_id: str | None,
) -> Any:
    """Add an item. A retry with the ``idempotency_key`` of an earlier, identical request returns
    that item instead of failing with ``DUPLICATE_NAME`` because the first attempt worked."""
    require(principal, Action.MANAGE_CATALOGUES)
    organization_id = _organization_id(principal)
    item_id = new_id()
    if idempotency_key is not None:
        item_id = claim(
            session,
            actor_user_id=principal.user_id,
            operation=f"create_{catalogue.entity_type}",
            key=idempotency_key,
            # The coaching is part of the request: a platform admin's key never reaches into
            # another coaching they acted in.
            body={**values, "organization_id": str(organization_id)},
            new_resource_id=item_id,
        )
        existing = session.get(catalogue.model, item_id)
        if existing is not None:
            return existing
    item = catalogue.model(
        id=item_id, organization_id=organization_id, name_key=name_key(values["name"]), **values
    )
    session.add(item)
    _save(session, catalogue)
    record_event(
        session,
        action=f"{catalogue.action_prefix}_CREATED",
        entity_type=catalogue.entity_type,
        entity_id=item.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_acting(principal),
        request_id=request_id,
        after=_snapshot(catalogue, item),
    )
    return item


def _locked(session: Session, catalogue: Catalogue, item_id: UUID) -> Any:
    model = catalogue.model
    item = session.scalars(select(model).where(model.id == item_id).with_for_update()).first()
    if item is None:
        raise NotFound(f"No such {catalogue.noun}.")
    return item


def _finish_change(
    session: Session,
    principal: Principal,
    catalogue: Catalogue,
    item: Any,
    action: str,
    before: dict[str, Any],
    request_id: str | None,
) -> None:
    item.revision += 1
    item.updated_at = datetime.now(UTC)
    _save(session, catalogue)
    record_event(
        session,
        action=f"{catalogue.action_prefix}_{action}",
        entity_type=catalogue.entity_type,
        entity_id=item.id,
        organization_id=item.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_acting(principal),
        request_id=request_id,
        before=before,
        after=_snapshot(catalogue, item),
    )


def update_item(
    session: Session,
    principal: Principal,
    catalogue: Catalogue,
    item_id: UUID,
    changes: dict[str, Any],
    *,
    if_match: str | None,
    request_id: str | None,
) -> Any:
    """Apply ``changes`` (only the fields that were sent), refusing stale ones (If-Match).

    A change that changes nothing keeps the revision and writes no audit event.
    """
    require(principal, Action.MANAGE_CATALOGUES)
    item = _locked(session, catalogue, item_id)
    require_if_match(if_match, item.revision)
    before = _snapshot(catalogue, item)
    for field, value in changes.items():
        setattr(item, field, value)
        if field == "name":
            item.name_key = name_key(value)
    if _snapshot(catalogue, item) != before:
        _finish_change(session, principal, catalogue, item, "UPDATED", before, request_id)
    return item


def set_state(
    session: Session,
    principal: Principal,
    catalogue: Catalogue,
    item_id: UUID,
    state: str,
    *,
    if_match: str | None,
    request_id: str | None,
) -> Any:
    """Retire or restore an item. Asking for the state it already has changes nothing."""
    require(principal, Action.MANAGE_CATALOGUES)
    item = _locked(session, catalogue, item_id)
    require_if_match(if_match, item.revision)
    if item.state == state:
        return item
    before = _snapshot(catalogue, item)
    item.state = state
    action = "DEPRECATED" if state == "DEPRECATED" else "RESTORED"
    _finish_change(session, principal, catalogue, item, action, before, request_id)
    return item
