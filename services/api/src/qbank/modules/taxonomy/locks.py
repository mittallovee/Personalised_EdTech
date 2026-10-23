"""One lock per coaching for its syllabus, so an import is applied against a syllabus that cannot
change underneath it.

Every change to a syllabus item or a concept takes the lock in *shared* mode (changes go on side
by side, as before). Applying an import takes it *exclusively*: it waits for changes in progress,
holds off new ones until it commits, and so checks "has the syllabus changed since the preview?"
and writes without anyone slipping a change in between. Both are held until the transaction ends.
Always taken before any row lock, so the two kinds of caller cannot deadlock each other.
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from qbank.core.auth import Principal

_SHARED = text("SELECT pg_advisory_xact_lock_shared(hashtextextended(:name, 0))")
_EXCLUSIVE = text("SELECT pg_advisory_xact_lock(hashtextextended(:name, 0))")


def _name(organization_id: UUID) -> dict[str, str]:
    return {"name": f"syllabus:{organization_id}"}


def lock_syllabus_for_change(session: Session, principal: Principal) -> None:
    organization_id = principal.tenant_context.organization_id
    if organization_id is not None:  # a caller with no coaching has been refused already
        session.execute(_SHARED, _name(organization_id))


def lock_syllabus_for_import(session: Session, organization_id: UUID) -> None:
    session.execute(_EXCLUSIVE, _name(organization_id))
