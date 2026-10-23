"""Syllabus import previews (M3 design note §4.4, C-03): read a file, say what it would do.

Nothing here changes the syllabus. A preview is stored with the checked rows so that applying it
later (a separate step) acts on exactly what the admin saw.
"""

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.db import Database
from qbank.core.errors import NotFound
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.core.permissions import Action, require
from qbank.core.tenancy import TenantContext
from qbank.modules.taxonomy.import_file import read_table
from qbank.modules.taxonomy.import_plan import SnapConcept, SnapNode, Snapshot, build_plan
from qbank.modules.taxonomy.models import (
    CatalogueImport,
    Concept,
    ConceptAlias,
    ConceptLabel,
    TaxonomyLabel,
    TaxonomyNode,
)


def load_snapshot(database: Database, context: TenantContext) -> Snapshot:
    """The syllabus as it is now (row-level security limits it to the caller's coaching).

    Read in one repeatable-read transaction of its own, so the items, their labels and aliases
    all come from the same moment: a preview never mixes an item's old labels with its new
    revision, and the fingerprint stored with it describes exactly what was compared.
    """
    with database.transaction(context, isolation_level="REPEATABLE READ") as session:
        return _read_snapshot(session)


def _read_snapshot(session: Session) -> Snapshot:
    node_labels: dict[UUID, dict[str, str]] = defaultdict(dict)
    for node_id, language, label in session.execute(
        select(TaxonomyLabel.node_id, TaxonomyLabel.language, TaxonomyLabel.label)
    ):
        node_labels[node_id][language] = label
    nodes = [
        SnapNode(
            id=node.id,
            kind=node.kind,
            parent_id=node.parent_id,
            name_key=node.name_key,
            state=node.state,
            sort_order=node.sort_order,
            revision=node.revision,
            labels=node_labels[node.id],
        )
        for node in session.scalars(select(TaxonomyNode))
    ]
    concept_labels: dict[UUID, dict[str, str]] = defaultdict(dict)
    for concept_id, language, label in session.execute(
        select(ConceptLabel.concept_id, ConceptLabel.language, ConceptLabel.label)
    ):
        concept_labels[concept_id][language] = label
    alias_keys: dict[UUID, set[str]] = defaultdict(set)
    for concept_id, alias_key in session.execute(
        select(ConceptAlias.concept_id, ConceptAlias.alias_key)
    ):
        alias_keys[concept_id].add(alias_key)
    concepts = [
        SnapConcept(
            id=concept.id,
            subject_id=concept.subject_id,
            name=concept.name,
            name_key=concept.name_key,
            state=concept.state,
            revision=concept.revision,
            labels=concept_labels[concept.id],
            alias_keys=frozenset(alias_keys[concept.id]),
        )
        for concept in session.scalars(select(Concept))
    ]
    return Snapshot(nodes=nodes, concepts=concepts)


def create_preview(
    session: Session,
    principal: Principal,
    *,
    file_name: str,
    data: bytes,
    snapshot: Snapshot,
    idempotency_key: str | None,
) -> CatalogueImport:
    """Work out what the file would do to ``snapshot`` and keep the result. Changes no item.

    ``snapshot`` is the syllabus as read by ``load_snapshot``. A retry with the
    ``idempotency_key`` of an earlier request for the same file returns the preview that request
    made. A file that cannot be read at all is an ``IMPORT_INVALID`` error; a file with problem
    rows is a preview whose rows say so.
    """
    require(principal, Action.MANAGE_CATALOGUES)
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise NotFound("No such coaching.")
    digest = hashlib.sha256(data).hexdigest()
    import_id = new_id()
    if idempotency_key is not None:
        import_id = claim(
            session,
            actor_user_id=principal.user_id,
            operation="create_catalogue_import",
            key=idempotency_key,
            body={"file_sha256": digest, "organization_id": str(organization_id)},
            new_resource_id=import_id,
        )
        existing = session.get(CatalogueImport, import_id)
        if existing is not None:
            return existing
    plan = build_plan(read_table(data), snapshot)
    preview = CatalogueImport(
        id=import_id,
        organization_id=organization_id,
        created_by=principal.user_id,
        file_name=file_name,
        file_sha256=digest,
        counts=plan.counts,
        base_fingerprint=plan.base_fingerprint,
        rows=[row.as_json() for row in plan.rows],
    )
    session.add(preview)
    session.flush()
    return preview


def get_import(session: Session, import_id: UUID) -> CatalogueImport:
    found = session.get(CatalogueImport, import_id)  # row-level security hides other coachings'
    if found is None:
        raise NotFound("No such import.")
    return found


def list_rows(
    preview: CatalogueImport, *, status: str | None, after: int, limit: int
) -> tuple[Sequence[dict[str, object]], bool]:
    """A page of the preview's rows in file order, after row number ``after``."""
    matching = (
        row
        for row in preview.rows
        if row["number"] > after and (status is None or row["status"] == status)
    )
    page = [row for _, row in zip(range(limit + 1), matching, strict=False)]
    return page[:limit], len(page) > limit
