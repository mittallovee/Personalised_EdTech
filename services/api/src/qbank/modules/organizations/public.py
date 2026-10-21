"""Public interface of the organizations module. Other modules import only from here."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.modules.organizations.models import Membership, MembershipGrant, Organization


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


def membership_grants(session: Session, membership_id: UUID) -> frozenset[str]:
    """The faculty grants of a membership. Needs its coaching in the tenant context."""
    return frozenset(
        session.scalars(
            select(MembershipGrant.grant_name).where(MembershipGrant.membership_id == membership_id)
        )
    )


def lock_membership(session: Session, membership_id: UUID) -> None:
    """Hold the membership row until the transaction ends, so changes for one member (e.g. issuing
    a new link) run one after another. Needs its coaching in the tenant context."""
    session.execute(select(Membership.id).where(Membership.id == membership_id).with_for_update())
