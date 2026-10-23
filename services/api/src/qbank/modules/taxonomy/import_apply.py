"""Applying a previewed syllabus import (M3 design note §4.4, C-03).

Everything happens in one transaction, so a file is applied completely or not at all. It acts on
the rows stored with the preview, exactly as the admin saw them, and goes through the same service
functions as the screens do (permissions, the rules for names and aliases, audit events), so an
import can never do what an admin could not. Nothing is removed, renamed, retired or restored.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, PreconditionFailed
from qbank.core.etag import etag
from qbank.core.permissions import Action, require
from qbank.modules.audit.public import record_event
from qbank.modules.taxonomy import concepts, service
from qbank.modules.taxonomy.catalogues import name_key
from qbank.modules.taxonomy.import_file import ImportFileInvalid
from qbank.modules.taxonomy.import_plan import (
    CONCEPT,
    MAX_APPLY_ROWS,
    SnapConcept,
    Snapshot,
    apply_order,
    node_index,
)
from qbank.modules.taxonomy.import_service import read_snapshot
from qbank.modules.taxonomy.locks import lock_syllabus_for_import
from qbank.modules.taxonomy.models import CatalogueImport
from qbank.modules.taxonomy.schemas import CreateConcept, CreateNode, UpdateConcept, UpdateNode


def _stale() -> Conflict:
    return Conflict(
        "The syllabus changed after this preview was made. Upload the file again to see what it"
        " would do now.",
        code="IMPORT_STALE",
    )


def apply_import(
    session: Session,
    principal: Principal,
    import_id: UUID,
    *,
    request_id: str | None,
) -> CatalogueImport:
    """Apply the preview.

    Takes the coaching's syllabus lock exclusively first (see ``locks``), so no change to the
    syllabus can slip in between the staleness check and the writes, and two imports cannot apply
    at the same time.

    Applying twice is safe: the second call finds it applied and changes nothing. Refused with
    ``IMPORT_INVALID`` if a row is an error, there is nothing to do, or it is too much at once;
    with ``IMPORT_STALE`` if the syllabus is not what the preview was made against.
    """
    require(principal, Action.MANAGE_CATALOGUES)
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise NotFound("No such import.")
    lock_syllabus_for_import(session, organization_id)
    preview = session.scalars(
        select(CatalogueImport).where(CatalogueImport.id == import_id).with_for_update()
    ).first()  # locked: two people applying at once take turns
    if preview is None:
        raise NotFound("No such import.")
    if preview.state == "APPLIED":
        return preview
    counts = preview.counts
    if counts["ERROR"]:
        raise ImportFileInvalid(
            f"{counts['ERROR']} row(s) cannot be imported. Fix them in the file and upload it"
            " again."
        )
    actionable = counts["NEW"] + counts["CHANGED"]
    if actionable == 0:
        raise ImportFileInvalid("There is nothing to import: every row is already in the syllabus.")
    if actionable > MAX_APPLY_ROWS:
        raise ImportFileInvalid(
            f"This would add or change {actionable:,} rows; at most {MAX_APPLY_ROWS:,} at once."
            " Split the file and import the parts one after another."
        )
    snapshot = read_snapshot(session)
    if snapshot.fingerprint() != preview.base_fingerprint:
        raise _stale()

    try:
        _write_rows(session, principal, preview.rows, snapshot, request_id)
    except Conflict, PreconditionFailed:
        # Someone added or changed the same thing between the preview and now.
        raise _stale() from None

    preview.state = "APPLIED"
    preview.applied_at = datetime.now(UTC)
    session.flush()
    record_event(
        session,
        action="CATALOGUE_IMPORT_APPLIED",
        entity_type="catalogue_import",
        entity_id=preview.id,
        organization_id=preview.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        after={
            "file_name": preview.file_name,
            "file_sha256": preview.file_sha256,
            "added": counts["NEW"],
            "changed": counts["CHANGED"],
        },
    )
    return preview


def _write_rows(
    session: Session,
    principal: Principal,
    rows: list[dict[str, Any]],
    snapshot: Snapshot,
    request_id: str | None,
) -> None:
    index = node_index(snapshot)
    ids: dict[tuple[str, ...], UUID] = {path: node.id for path, node in index.items()}
    existing_concepts: dict[tuple[UUID, str], SnapConcept] = {
        (concept.subject_id, concept.name_key): concept for concept in snapshot.concepts
    }
    for row in sorted(rows, key=apply_order):
        if row["status"] not in ("NEW", "CHANGED"):
            continue
        keys = tuple(name_key(name) for name in row["names"])
        if row["kind"] == CONCEPT:
            _write_concept(
                session, principal, row, ids[keys[:2]], existing_concepts, keys[2], request_id
            )
        elif row["status"] == "NEW":
            created = service.create_node(
                session,
                principal,
                CreateNode.model_validate(
                    {
                        "kind": row["kind"],
                        "parent_id": ids[keys[:-1]] if len(keys) > 1 else None,
                        "name": row["names"][-1],
                        "labels": row["labels"],
                        "sort_order": row["sort_order"] or 0,
                    }
                ),
                idempotency_key=None,
                request_id=request_id,
            )
            ids[keys] = created.id
        else:
            node = index[keys]
            service.update_node(
                session,
                principal,
                node.id,
                UpdateNode.model_validate(
                    {"labels": {**node.labels, **row["labels"]}, "sort_order": row["sort_order"]}
                ),
                if_match=etag(node.revision),
                request_id=request_id,
            )


def _write_concept(
    session: Session,
    principal: Principal,
    row: dict[str, Any],
    subject_id: UUID,
    existing: dict[tuple[UUID, str], SnapConcept],
    concept_key: str,
    request_id: str | None,
) -> None:
    if row["status"] == "NEW":
        concepts.create_concept(
            session,
            principal,
            CreateConcept.model_validate(
                {
                    "subject_id": subject_id,
                    "name": row["names"][2],
                    "labels": row["labels"],
                    "aliases": row["aliases"],
                }
            ),
            idempotency_key=None,
            request_id=request_id,
        )
        return
    concept = existing[(subject_id, concept_key)]
    added = list(
        {
            name_key(alias): alias
            for alias in reversed(row["aliases"])
            if name_key(alias) not in concept.aliases
        }.values()
    )[::-1]  # one spelling for each new alias, the first the file gave
    concepts.update_concept(
        session,
        principal,
        concept.id,
        UpdateConcept.model_validate(
            {
                "labels": {**concept.labels, **row["labels"]},
                "aliases": [*concept.aliases.values(), *added],
            }
        ),
        if_match=etag(concept.revision),
        request_id=request_id,
    )
