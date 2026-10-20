"""Public interface of the identity module. Other modules import only from here."""

from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.modules.identity.models import User


def display_names(session: Session, user_ids: Collection[UUID]) -> dict[UUID, str]:
    """Names of the given users that the current tenant context may see (others are left out)."""
    if not user_ids:
        return {}
    rows = session.execute(select(User.id, User.display_name).where(User.id.in_(user_ids)))
    return {row.id: row.display_name for row in rows}
