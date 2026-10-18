"""Public interface of the organizations module. Other modules import only from here."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.modules.organizations.models import Membership, Organization


@dataclass(frozen=True, slots=True)
class MembershipInfo:
    membership_id: UUID
    organization_id: UUID
    role: str


@dataclass(frozen=True, slots=True)
class OrganizationInfo:
    id: UUID
    display_name: str
    status: str


def find_active_membership(session: Session, user_id: UUID) -> MembershipInfo | None:
    """The user's active membership (at most one, B-07). Needs ``user_id`` in the tenant context."""
    row = session.scalars(
        select(Membership).where(Membership.user_id == user_id, Membership.status == "ACTIVE")
    ).first()
    if row is None:
        return None
    return MembershipInfo(row.id, row.organization_id, row.role)


def get_organization(session: Session, organization_id: UUID) -> OrganizationInfo | None:
    """Needs that coaching (or platform authority) in the tenant context."""
    row = session.get(Organization, organization_id)
    if row is None:
        return None
    return OrganizationInfo(row.id, row.display_name, row.status)
