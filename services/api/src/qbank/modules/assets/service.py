"""Storing and finding pictures. The picture has already been checked and re-encoded."""

import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import NotFound
from qbank.core.ids import new_id
from qbank.core.storage import Storage
from qbank.modules.assets.images import CleanImage
from qbank.modules.assets.models import Asset


def create_image(
    session: Session, principal: Principal, storage: Storage, picture: CleanImage
) -> Asset:
    """Keep the picture in storage and write its row.

    The key is opaque: it names the coaching and a fresh id, never anything the uploader typed.
    """
    organization_id = principal.tenant_context.organization_id
    asset_id = new_id()
    key = f"org/{organization_id}/image/{asset_id}"
    storage.put(key, picture.data)
    asset = Asset(
        id=asset_id,
        organization_id=organization_id,
        kind="IMAGE",
        content_type=picture.content_type,
        byte_size=len(picture.data),
        sha256=hashlib.sha256(picture.data).hexdigest(),
        width=picture.width,
        height=picture.height,
        storage_key=key,
        created_by=principal.user_id,
    )
    try:
        session.add(asset)
        session.flush()
    except Exception:
        storage.delete(key)  # no row, so nothing may keep pointing at the file
        raise
    return asset


def get_asset(session: Session, asset_id: UUID) -> Asset:
    """The coaching's own picture; another coaching's id is not found (row-level security)."""
    asset = session.scalars(select(Asset).where(Asset.id == asset_id)).one_or_none()
    if asset is None:
        raise NotFound("No such picture.")
    return asset
