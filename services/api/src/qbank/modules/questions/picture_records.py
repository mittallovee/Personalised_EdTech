"""Recording which pictures a saved revision uses (M3 design note §5.7).

The same bookkeeping serves question revisions and passage revisions: a table with one row per
picture a revision uses. Only this coaching's own pictures are recorded (a missing or foreign one
is a finding, not a row). A picture that a saved revision uses cannot be deleted, so this is what
keeps history showing its pictures. The rows of a frozen revision are never touched (the database
refuses).
"""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from qbank.modules.assets.public import existing_image_ids
from qbank.modules.questions.image_checks import image_ids
from qbank.modules.questions.models import PassageRevisionAsset, RevisionAsset


def record_pictures(
    session: Session,
    table: type[RevisionAsset] | type[PassageRevisionAsset],
    *,
    organization_id: UUID,
    revision_id: UUID,
    content: Any,
) -> None:
    """Make the pictures recorded for a working revision match its content."""
    wanted = existing_image_ids(session, image_ids(content))
    have = set(session.scalars(select(table.asset_id).where(table.revision_id == revision_id)))
    if have - wanted:
        session.execute(
            delete(table).where(table.revision_id == revision_id, table.asset_id.in_(have - wanted))
        )
    for asset_id in wanted - have:
        session.add(
            table(organization_id=organization_id, revision_id=revision_id, asset_id=asset_id)
        )
    session.flush()
