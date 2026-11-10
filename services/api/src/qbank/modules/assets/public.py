"""Public interface of the assets module. Other modules import only from here."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.modules.assets.images import MAX_BYTES, MAX_PIXELS
from qbank.modules.assets.models import Asset

__all__ = ["MAX_BYTES", "MAX_PIXELS", "existing_image_ids"]


def existing_image_ids(session: Session, ids: Collection[UUID]) -> set[UUID]:
    """Which of these ids are pictures of the coaching the session works for.

    Row-level security hides every other coaching's pictures, so an id from elsewhere is simply
    not in the answer, exactly like an id that does not exist.
    """
    if not ids:
        return set()
    return set(session.scalars(select(Asset.id).where(Asset.id.in_(ids), Asset.kind == "IMAGE")))
