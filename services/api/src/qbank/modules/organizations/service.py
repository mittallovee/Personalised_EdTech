"""Platform administration of coachings (A-04): create one with its first Owner, list them."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import NotFound
from qbank.core.etag import require_if_match
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
    revoke_coaching_sessions,
    set_acting_organization,
    user_status,
)
from qbank.modules.organizations.models import Membership, Organization
from qbank.modules.organizations.schemas import CreateOrganization, UpdateOrganization


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
    owner = Membership(organization_id=organization_id, user_id=owner_id, role="OWNER")
    session.add(owner)
    session.flush()
    reserve_email(session, owner_id, body.owner.email)  # needs the membership to exist
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


def _locked_organization(session: Session, organization_id: UUID) -> Organization:
    """The coaching, locked until the transaction ends so changes to it run one after another."""
    organization = session.scalars(
        select(Organization).where(Organization.id == organization_id).with_for_update()
    ).first()
    if organization is None:
        raise NotFound("No such coaching.")
    return organization


def _snapshot(organization: Organization) -> dict[str, object]:
    return {
        "display_name": organization.display_name,
        "timezone": organization.timezone,
        "status": organization.status,
    }


def _record_change(
    session: Session,
    principal: Principal,
    organization: Organization,
    action: str,
    before: dict[str, object],
    request_id: str | None,
) -> None:
    organization.revision += 1
    organization.updated_at = datetime.now(UTC)
    session.flush()
    record_event(
        session,
        action=action,
        entity_type="organization",
        entity_id=organization.id,
        organization_id=organization.id,
        actor_user_id=principal.user_id,
        actor_is_platform=True,
        request_id=request_id,
        before=before,
        after=_snapshot(organization),
    )


def update_organization(
    session: Session,
    principal: Principal,
    organization_id: UUID,
    body: UpdateOrganization,
    *,
    if_match: str | None,
    request_id: str | None,
) -> Organization:
    """Rename or change the time zone (platform only, A-04), refusing stale changes (If-Match)."""
    apply_tenant_context(session, creation_context(principal, organization_id))
    organization = _locked_organization(session, organization_id)
    require_if_match(if_match, organization.revision)
    before = _snapshot(organization)
    if body.display_name is not None:
        organization.display_name = body.display_name
    if body.timezone is not None:
        organization.timezone = body.timezone
    if _snapshot(organization) != before:
        _record_change(session, principal, organization, "COACHING_UPDATED", before, request_id)
    return organization


def set_status(
    session: Session,
    principal: Principal,
    organization_id: UUID,
    status: str,
    *,
    if_match: str | None,
    request_id: str | None,
) -> Organization:
    """Suspend or reactivate (A-07), refusing stale requests (If-Match).

    Asking for the current status changes nothing. Suspending also ends the members' sessions,
    so after a reactivation everyone signs in again.
    """
    apply_tenant_context(session, creation_context(principal, organization_id))
    organization = _locked_organization(session, organization_id)
    require_if_match(if_match, organization.revision)
    if organization.status != status:
        before = _snapshot(organization)
        organization.status = status
        action = "COACHING_SUSPENDED" if status == "SUSPENDED" else "COACHING_REACTIVATED"
        if status == "SUSPENDED":
            revoke_coaching_sessions(session, organization_id)
        _record_change(session, principal, organization, action, before, request_id)
    return organization


def act_in(
    session: Session,
    principal: Principal,
    organization_id: UUID | None,
    *,
    request_id: str | None,
) -> None:
    """Start (or with None, stop) acting inside a coaching for this sign-in session (A-06).

    Recorded in the coaching's audit log, so its admins can see when platform staff were in it.
    """
    if principal.session_id is None:
        raise NotFound("Acting in a coaching needs a sign-in session.")
    if organization_id is not None:
        apply_tenant_context(session, creation_context(principal, organization_id))
        if session.get(Organization, organization_id) is None:
            raise NotFound("No such coaching.")
    previous = set_acting_organization(session, principal.session_id, organization_id)
    for org_id, action in (
        (previous, "PLATFORM_ACTING_STOPPED"),
        (organization_id, "PLATFORM_ACTING_STARTED"),
    ):
        if org_id is None or previous == organization_id:
            continue
        apply_tenant_context(session, creation_context(principal, org_id))
        record_event(
            session,
            action=action,
            entity_type="organization",
            entity_id=org_id,
            organization_id=org_id,
            actor_user_id=principal.user_id,
            actor_is_platform=True,
            request_id=request_id,
        )
