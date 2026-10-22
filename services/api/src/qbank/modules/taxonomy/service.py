"""The syllabus tree (M3 design note §4.1): add, rename, order, retire and restore items."""

import base64
import binascii
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, MalformedRequest, NotFound, ValidationFailed
from qbank.core.etag import require_if_match
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.modules.audit.public import record_event
from qbank.modules.taxonomy.catalogues import name_key
from qbank.modules.taxonomy.models import TaxonomyLabel, TaxonomyNode
from qbank.modules.taxonomy.schemas import CreateNode, NodeOut, UpdateNode

# The kind a node of each kind hangs under (None: it is at the top).
PARENT_KIND: dict[str, str | None] = {
    "CLASS": None,
    "SUBJECT": "CLASS",
    "CHAPTER": "SUBJECT",
    "TOPIC": "CHAPTER",
    "SUBTOPIC": "TOPIC",
}

_SIBLING_NAME_INDEX = "taxonomy_nodes_sibling_name"


def _acting(principal: Principal) -> bool:
    return principal.acting_organization_id is not None


def _organization_id(principal: Principal) -> UUID:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise NotFound("No such syllabus item.")
    return organization_id


# --- Reading ----------------------------------------------------------------------------------


def _encode_position(node: TaxonomyNode) -> str:
    raw = json.dumps([node.sort_order, node.name_key, str(node.id)]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_position(cursor: str) -> tuple[int, str, UUID]:
    """Inverse of ``next_cursor``; a damaged cursor is a 400, never a 500."""
    invalid = MalformedRequest("The page cursor is not valid. Start again from the first page.")
    try:
        data = json.loads(base64.urlsafe_b64decode((cursor + "=" * (-len(cursor) % 4)).encode()))
    except binascii.Error, UnicodeDecodeError, ValueError:
        raise invalid from None
    if not (
        isinstance(data, list)
        and len(data) == 3
        and isinstance(data[0], int)
        and not isinstance(data[0], bool)
        and isinstance(data[1], str)
        and isinstance(data[2], str)
    ):
        raise invalid
    try:
        return data[0], data[1], UUID(data[2])
    except ValueError:
        raise invalid from None


def next_cursor(nodes: Sequence[TaxonomyNode], has_more: bool) -> str | None:
    return _encode_position(nodes[-1]) if has_more and nodes else None


def list_nodes(
    session: Session,
    *,
    kind: str | None,
    parent_id: UUID | None,
    state: str | None,
    limit: int,
    after: tuple[int, str, UUID] | None,
) -> tuple[list[TaxonomyNode], bool]:
    """In the admin's order (sort order, then name). Returns the page and whether more follow."""
    query = select(TaxonomyNode).order_by(
        TaxonomyNode.sort_order, TaxonomyNode.name_key, TaxonomyNode.id
    )
    if kind is not None:
        query = query.where(TaxonomyNode.kind == kind)
    if parent_id is not None:
        query = query.where(TaxonomyNode.parent_id == parent_id)
    if state is not None:
        query = query.where(TaxonomyNode.state == state)
    if after is not None:
        sort_order, key, node_id = after
        query = query.where(
            (TaxonomyNode.sort_order > sort_order)
            | ((TaxonomyNode.sort_order == sort_order) & (TaxonomyNode.name_key > key))
            | (
                (TaxonomyNode.sort_order == sort_order)
                & (TaxonomyNode.name_key == key)
                & (TaxonomyNode.id > node_id)
            )
        )
    rows = list(session.scalars(query.limit(limit + 1)))
    return rows[:limit], len(rows) > limit


def get_node(session: Session, node_id: UUID) -> TaxonomyNode:
    node = session.get(TaxonomyNode, node_id)  # row-level security hides other coachings' items
    if node is None:
        raise NotFound("No such syllabus item.")
    return node


def describe(session: Session, nodes: Sequence[TaxonomyNode]) -> list[NodeOut]:
    labels: dict[UUID, dict[str, str]] = {node.id: {} for node in nodes}
    if nodes:
        for label in session.scalars(
            select(TaxonomyLabel).where(TaxonomyLabel.node_id.in_(list(labels)))
        ):
            labels[label.node_id][label.language] = label.label
    return [
        NodeOut(
            id=node.id,
            kind=node.kind,
            parent_id=node.parent_id,
            name=node.name,
            labels=labels[node.id],
            state=node.state,
            sort_order=node.sort_order,
            revision=node.revision,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )
        for node in nodes
    ]


# --- Changing ---------------------------------------------------------------------------------


def _snapshot(node: TaxonomyNode, labels: dict[str, str]) -> dict[str, Any]:
    return {
        "kind": node.kind,
        "parent_id": str(node.parent_id) if node.parent_id else None,
        "name": node.name,
        "labels": dict(sorted(labels.items())),
        "state": node.state,
        "sort_order": node.sort_order,
    }


def _current_labels(session: Session, node_id: UUID) -> dict[str, str]:
    return {
        label.language: label.label
        for label in session.scalars(select(TaxonomyLabel).where(TaxonomyLabel.node_id == node_id))
    }


def _save(session: Session) -> None:
    """Flush, turning "a sibling already has this name" into a clear 409."""
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as error:
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        if constraint == _SIBLING_NAME_INDEX:
            raise Conflict(
                "Another item under the same parent already has this name.",
                code="DUPLICATE_NAME",
            ) from None
        raise


def _lock_parent(session: Session, parent_id: UUID) -> TaxonomyNode:
    """The parent, held until the transaction ends so it is not retired while a child is added."""
    parent = session.scalars(
        select(TaxonomyNode).where(TaxonomyNode.id == parent_id).with_for_update(read=True)
    ).first()
    if parent is None:
        raise NotFound("No such parent item.")
    return parent


def create_node(
    session: Session,
    principal: Principal,
    body: CreateNode,
    *,
    idempotency_key: str | None,
    request_id: str | None,
) -> TaxonomyNode:
    """Add an item. A retry with the ``idempotency_key`` of an earlier, identical request returns
    that item instead of failing with ``DUPLICATE_NAME`` because the first attempt worked."""
    organization_id = _organization_id(principal)
    node_id = new_id()
    if idempotency_key is not None:
        node_id = claim(
            session,
            actor_user_id=principal.user_id,
            operation="create_taxonomy_node",
            key=idempotency_key,
            # The coaching is part of the request: a platform admin's key never reaches into
            # another coaching they acted in.
            body={**body.model_dump(mode="json"), "organization_id": str(organization_id)},
            new_resource_id=node_id,
        )
        existing = session.get(TaxonomyNode, node_id)
        if existing is not None:
            return existing
    expected = PARENT_KIND[body.kind]
    parent: TaxonomyNode | None = None
    if expected is None:
        if body.parent_id is not None:
            raise ValidationFailed("A class has no parent.", code="HIERARCHY_INVALID")
    else:
        if body.parent_id is None:
            raise ValidationFailed(
                f"A {body.kind.lower()} belongs under a {expected.lower()}.",
                code="HIERARCHY_INVALID",
            )
        parent = _lock_parent(session, body.parent_id)
        if parent.kind != expected:
            raise ValidationFailed(
                f"A {body.kind.lower()} belongs under a {expected.lower()}, not a"
                f" {parent.kind.lower()}.",
                code="HIERARCHY_INVALID",
            )
        if parent.state != "ACTIVE":
            raise Conflict("The parent item is retired.", code="PARENT_DEPRECATED")
    node = TaxonomyNode(
        id=node_id,
        organization_id=organization_id,
        kind=body.kind,
        parent_id=parent.id if parent else None,
        parent_kind=parent.kind if parent else None,
        name=body.name,
        name_key=name_key(body.name),
        sort_order=body.sort_order,
    )
    session.add(node)
    _save(session)
    for language, label in body.labels.items():
        session.add(
            TaxonomyLabel(
                organization_id=organization_id, node_id=node.id, language=language, label=label
            )
        )
    session.flush()
    record_event(
        session,
        action="TAXONOMY_NODE_CREATED",
        entity_type="taxonomy_node",
        entity_id=node.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_acting(principal),
        request_id=request_id,
        after=_snapshot(node, body.labels),
    )
    return node


def _locked_node(session: Session, node_id: UUID) -> TaxonomyNode:
    node = session.scalars(
        select(TaxonomyNode).where(TaxonomyNode.id == node_id).with_for_update()
    ).first()
    if node is None:
        raise NotFound("No such syllabus item.")
    return node


def _finish_change(
    session: Session,
    principal: Principal,
    node: TaxonomyNode,
    action: str,
    before: dict[str, Any],
    request_id: str | None,
) -> None:
    node.revision += 1
    node.updated_at = datetime.now(UTC)
    _save(session)
    record_event(
        session,
        action=action,
        entity_type="taxonomy_node",
        entity_id=node.id,
        organization_id=node.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_acting(principal),
        request_id=request_id,
        before=before,
        after=_snapshot(node, _current_labels(session, node.id)),
    )


def update_node(
    session: Session,
    principal: Principal,
    node_id: UUID,
    body: UpdateNode,
    *,
    if_match: str | None,
    request_id: str | None,
) -> TaxonomyNode:
    """Rename, reorder or change the other-language names, refusing stale changes (If-Match)."""
    node = _locked_node(session, node_id)
    require_if_match(if_match, node.revision)
    labels = _current_labels(session, node.id)
    before = _snapshot(node, labels)
    if body.name is not None:
        node.name = body.name
        node.name_key = name_key(body.name)
    if body.sort_order is not None:
        node.sort_order = body.sort_order
    if body.labels is not None and body.labels != labels:
        for language in labels.keys() - body.labels.keys():
            session.execute(
                delete(TaxonomyLabel).where(
                    TaxonomyLabel.node_id == node.id, TaxonomyLabel.language == language
                )
            )
        for language, label in body.labels.items():
            existing = session.get(TaxonomyLabel, (node.id, language))
            if existing is None:
                session.add(
                    TaxonomyLabel(
                        organization_id=node.organization_id,
                        node_id=node.id,
                        language=language,
                        label=label,
                    )
                )
            else:
                existing.label = label
    _save(session)  # before any query, so a name clash surfaces as the 409 and not as a raw error
    if _snapshot(node, _current_labels(session, node.id)) != before:
        _finish_change(session, principal, node, "TAXONOMY_NODE_UPDATED", before, request_id)
    return node


def set_state(
    session: Session,
    principal: Principal,
    node_id: UUID,
    state: str,
    *,
    if_match: str | None,
    request_id: str | None,
) -> TaxonomyNode:
    """Retire or restore an item. Asking for the state it already has changes nothing.

    Retiring never touches the item's children or the questions that use it. Restoring is refused
    while its parent is retired, so an active item never hangs under a retired one by restoring.
    """
    node = _locked_node(session, node_id)
    require_if_match(if_match, node.revision)
    if node.state == state:
        return node
    if (
        state == "ACTIVE"
        and node.parent_id is not None
        and _lock_parent(session, node.parent_id).state != "ACTIVE"
    ):
        raise Conflict("Restore the parent item first.", code="PARENT_DEPRECATED")
    before = _snapshot(node, _current_labels(session, node.id))
    node.state = state
    action = "TAXONOMY_NODE_DEPRECATED" if state == "DEPRECATED" else "TAXONOMY_NODE_RESTORED"
    _finish_change(session, principal, node, action, before, request_id)
    return node
