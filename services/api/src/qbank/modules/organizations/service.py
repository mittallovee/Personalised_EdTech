"""Platform administration of coachings (A-04): create one with its first Owner, list them."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext, apply_tenant_context
from qbank.modules.audit.public import record_event
from qbank.modules.identity.public import (
    INVITED,
    IssuedLink,
    LinkPurpose,
    create_invited_user,
    issue_account_link,
    reserve_email,
    user_status,
)
from qbank.modules.organizations.models import Membership, Organization
from qbank.modules.organizations.schemas import CreateOrganization


def creation_context(principal: Principal, organization_id: UUID) -> TenantContext:
    """Platform authority, inside the (new) coaching so its memberships and links can be written."""
    return TenantContext(
        organization_id=organization_id, user_id=principal.user_id, is_platform=True
    )


def create_organization(
    session: Session,
    principal: Principal,
    body: CreateOrganization,
    *,
    idempotency_key: str | None,
    request_id: str | None,
) -> tuple[Organization, Membership, IssuedLink | None]:
    """Create the coaching, its Owner (invited) and the Owner's activation link, all or nothing.

    With an ``idempotency_key`` already used for the same body, nothing new is created: the
    earlier coaching and Owner are returned with a fresh activation link (the first one was never
    seen, because the response was lost), unless the Owner has activated meanwhile.
    """
    organization_id = new_id()
    if idempotency_key is not None:
        apply_tenant_context(session, TenantContext(user_id=principal.user_id, is_platform=True))
        organization_id = claim(
            session,
            actor_user_id=principal.user_id,
            operation="create_organization",
            key=idempotency_key,
            body=body.model_dump(mode="json"),
            new_resource_id=organization_id,
        )
    apply_tenant_context(session, creation_context(principal, organization_id))
    existing = session.get(Organization, organization_id)
    if existing is not None:
        return _reissue_owner_link(session, principal, existing, request_id)

    organization = Organization(
        id=organization_id, display_name=body.display_name, timezone=body.timezone
    )
    session.add(organization)
    session.flush()
    owner_id = create_invited_user(session, body.owner.display_name)
    reserve_email(session, owner_id, body.owner.email)
    owner = Membership(organization_id=organization_id, user_id=owner_id, role="OWNER")
    session.add(owner)
    session.flush()
    link = issue_account_link(
        session,
        organization_id=organization_id,
        membership_id=owner.id,
        user_id=owner_id,
        purpose=LinkPurpose.ACTIVATION,
        created_by=principal.user_id,
    )
    record_event(
        session,
        action="COACHING_CREATED",
        entity_type="organization",
        entity_id=organization_id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=True,
        request_id=request_id,
        after={
            "display_name": organization.display_name,
            "timezone": organization.timezone,
            "owner": {
                "user_id": str(owner_id),
                "display_name": body.owner.display_name,
                "email": body.owner.email.strip().lower(),
            },
        },
    )
    session.refresh(organization)
    return organization, owner, link


def _reissue_owner_link(
    session: Session, principal: Principal, organization: Organization, request_id: str | None
) -> tuple[Organization, Membership, IssuedLink | None]:
    # The member the first request invited: the coaching's first membership, created in the same
    # transaction as the coaching. Not "the current Owner": ownership may have moved since.
    owner = session.scalars(
        select(Membership)
        .where(Membership.organization_id == organization.id)
        .order_by(Membership.created_at, Membership.id)
    ).first()
    if owner is None:  # cannot happen: the Owner is created with the coaching, never deleted
        raise RuntimeError(f"coaching {organization.id} has no members")
    if owner.status != "ACTIVE" or user_status(session, owner.user_id) != INVITED:
        return organization, owner, None
    link = issue_account_link(
        session,
        organization_id=organization.id,
        membership_id=owner.id,
        user_id=owner.user_id,
        purpose=LinkPurpose.ACTIVATION,
        created_by=principal.user_id,
    )
    record_event(
        session,
        action="ACTIVATION_LINK_REISSUED",
        entity_type="user",
        entity_id=owner.user_id,
        organization_id=organization.id,
        actor_user_id=principal.user_id,
        actor_is_platform=True,
        request_id=request_id,
        after={"reason": "retried coaching creation"},
    )
    return organization, owner, link


def list_organizations(
    session: Session, *, limit: int, after: tuple[datetime, UUID] | None
) -> tuple[list[Organization], bool]:
    """Newest first. Needs platform authority (row-level security shows all coachings to it)."""
    query = select(Organization).order_by(Organization.created_at.desc(), Organization.id.desc())
    if after is not None:
        query = query.where(tuple_(Organization.created_at, Organization.id) < after)
    rows = list(session.scalars(query.limit(limit + 1)))
    return rows[:limit], len(rows) > limit
