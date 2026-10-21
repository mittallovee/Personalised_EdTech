"""A coaching's members (M2 PR 5): list them, invite new ones, make new activation or reset links.

Everything happens inside the principal's coaching (its own, or the one a platform admin acts in),
so row-level security keeps every query to that coaching. Who may do what is decided in
``core/permissions.py``; this module applies it to the member's **current** role, read under a
lock, so a screen that is a minute old can't act on someone who was promoted meanwhile.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, tuple_
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound
from qbank.core.etag import require_if_match
from qbank.core.idempotency import claim
from qbank.core.ids import new_id
from qbank.core.permissions import (
    Action,
    Grant,
    is_allowed,
    may_manage_member,
    require,
    require_may_manage_member,
)
from qbank.modules.audit.public import record_event
from qbank.modules.identity.public import (
    INVITED,
    IssuedLink,
    LinkPurpose,
    create_invited_user,
    issue_account_link,
    member_accounts,
    reserve_email,
    user_status,
)
from qbank.modules.organizations.models import Membership, MembershipGrant
from qbank.modules.organizations.schemas import InviteMember, MemberOut

NEW_ACTIVATION_LINK = "NEW_ACTIVATION_LINK"
NEW_RESET_LINK = "NEW_RESET_LINK"
SET_GRANTS = "SET_GRANTS"
# The link each account status can use; a disabled account gets none (redeeming would fail).
_LINK_FOR_STATUS = {INVITED: NEW_ACTIVATION_LINK, "ACTIVE": NEW_RESET_LINK}


def _coaching(principal: Principal) -> UUID:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # cannot happen: the permission check needs a coaching
        raise RuntimeError("members are only reachable inside a coaching")
    return organization_id


def _is_platform(principal: Principal) -> bool:
    return principal.acting_organization_id is not None


def describe(session: Session, principal: Principal, rows: Sequence[Membership]) -> list[MemberOut]:
    """Members as the API shows them, with the actions this principal may take on each."""
    accounts = member_accounts(session, {row.user_id for row in rows})
    grants: dict[UUID, list[str]] = {}
    for membership_id, grant in session.execute(
        select(MembershipGrant.membership_id, MembershipGrant.grant_name)
        .where(MembershipGrant.membership_id.in_([row.id for row in rows]))
        .order_by(MembershipGrant.grant_name)
    ):
        grants.setdefault(membership_id, []).append(grant)
    members = []
    for row in rows:
        account = accounts[row.user_id]
        actions = []
        link = _LINK_FOR_STATUS.get(account.status)
        if link and row.status == "ACTIVE" and may_manage_member(principal, row.role):
            actions.append(link)
        faculty = row.role == "FACULTY" and row.status == "ACTIVE"
        if faculty and is_allowed(principal, Action.MANAGE_FACULTY):
            actions.append(SET_GRANTS)
        members.append(
            MemberOut(
                membership_id=row.id,
                user_id=row.user_id,
                display_name=account.display_name,
                email=account.email,
                role=row.role,
                status=row.status,
                account_status=account.status,
                grants=grants.get(row.id, []),
                revision=row.revision,
                joined_at=row.created_at,
                actions=actions,
            )
        )
    return members


def list_members(
    session: Session, principal: Principal, *, limit: int, after: tuple[datetime, UUID] | None
) -> tuple[list[Membership], bool]:
    """Current (not removed) members, newest first."""
    query = (
        select(Membership)
        .where(Membership.organization_id == _coaching(principal), Membership.status == "ACTIVE")
        .order_by(Membership.created_at.desc(), Membership.id.desc())
    )
    if after is not None:
        query = query.where(tuple_(Membership.created_at, Membership.id) < after)
    rows = list(session.scalars(query.limit(limit + 1)))
    return rows[:limit], len(rows) > limit


def get_member(session: Session, membership_id: UUID, *, lock: bool = False) -> Membership:
    """A member of the current coaching (another coaching's members are not found)."""
    query = select(Membership).where(Membership.id == membership_id)
    if lock:  # wait for other changes to this member, then read what they left
        query = query.with_for_update().execution_options(populate_existing=True)
    member = session.scalars(query).first()
    if member is None:
        raise NotFound("No such member.")
    return member


def invite_member(
    session: Session,
    principal: Principal,
    body: InviteMember,
    *,
    idempotency_key: str | None,
    request_id: str | None,
) -> tuple[Membership, IssuedLink | None]:
    """Create an invited account, its membership and an activation link, all or nothing.

    With an ``idempotency_key`` already used for the same body (in this coaching), nothing new
    is created: the earlier member is returned with a fresh link (the first was never seen),
    unless they have activated or been removed meanwhile.
    """
    require_may_manage_member(principal, body.role)
    organization_id = _coaching(principal)
    membership_id = new_id()
    if idempotency_key is not None:
        membership_id = claim(
            session,
            actor_user_id=principal.user_id,
            operation="invite_member",
            key=idempotency_key,
            # The coaching is part of the request: a platform admin's key never reaches into
            # another coaching they acted in.
            body={**body.model_dump(mode="json"), "organization_id": str(organization_id)},
            new_resource_id=membership_id,
        )
        existing = session.get(Membership, membership_id)
        if existing is not None:
            return existing, _reissue(session, principal, existing, request_id)

    user_id = create_invited_user(session, body.display_name)
    member = Membership(
        id=membership_id, organization_id=organization_id, user_id=user_id, role=body.role
    )
    session.add(member)
    session.flush()
    reserve_email(session, user_id, body.email)  # needs the membership to exist
    link = issue_account_link(
        session,
        organization_id=organization_id,
        membership_id=member.id,
        user_id=user_id,
        purpose=LinkPurpose.ACTIVATION,
        created_by=principal.user_id,
    )
    record_event(
        session,
        action="MEMBER_INVITED",
        entity_type="membership",
        entity_id=member.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_is_platform(principal),
        request_id=request_id,
        after={
            "user_id": str(user_id),
            "display_name": body.display_name,
            "email": body.email.strip().lower(),
            "role": body.role,
        },
    )
    session.refresh(member)
    return member, link


def _reissue(
    session: Session, principal: Principal, member: Membership, request_id: str | None
) -> IssuedLink | None:
    member = get_member(session, member.id, lock=True)
    # The request was allowed for the role it named; the member may have been promoted since.
    require_may_manage_member(principal, member.role)
    if member.status != "ACTIVE" or user_status(session, member.user_id) != INVITED:
        return None
    return _issue(session, principal, member, LinkPurpose.ACTIVATION, request_id, retried=True)


def new_link(
    session: Session,
    principal: Principal,
    membership_id: UUID,
    purpose: LinkPurpose,
    *,
    request_id: str | None,
) -> IssuedLink:
    """A new activation link (for an invitee) or reset link (for an active account)."""
    require(principal, Action.MANAGE_FACULTY)  # the least anyone who makes links needs
    member = get_member(session, membership_id, lock=True)
    require_may_manage_member(principal, member.role)
    if member.status != "ACTIVE":
        raise Conflict("This person is no longer a member.", code="MEMBER_REMOVED")
    account_status = user_status(session, member.user_id)
    if account_status == "DISABLED":
        raise Conflict("This account is disabled.", code="ACCOUNT_DISABLED")
    invited = account_status == INVITED
    if purpose is LinkPurpose.ACTIVATION and not invited:
        raise Conflict(
            "This account is already activated. Make a password-reset link instead.",
            code="ALREADY_ACTIVATED",
        )
    if purpose is LinkPurpose.RESET and invited:
        raise Conflict(
            "This account is not activated yet. Make a new activation link instead.",
            code="NOT_ACTIVATED",
        )
    return _issue(session, principal, member, purpose, request_id)


def _issue(
    session: Session,
    principal: Principal,
    member: Membership,
    purpose: LinkPurpose,
    request_id: str | None,
    *,
    retried: bool = False,
) -> IssuedLink:
    link = issue_account_link(
        session,
        organization_id=member.organization_id,
        membership_id=member.id,
        user_id=member.user_id,
        purpose=purpose,
        created_by=principal.user_id,
    )
    if retried:
        action = "ACTIVATION_LINK_REISSUED"
    elif purpose is LinkPurpose.ACTIVATION:
        action = "ACTIVATION_LINK_ISSUED"
    else:
        action = "RESET_LINK_ISSUED"
    record_event(
        session,
        action=action,
        entity_type="user",
        entity_id=member.user_id,
        organization_id=member.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_is_platform(principal),
        request_id=request_id,
        after={"reason": "retried invitation"} if retried else None,
    )
    return link


def set_grants(
    session: Session,
    principal: Principal,
    membership_id: UUID,
    grants: set[Grant],
    *,
    if_match: str | None,
    request_id: str | None,
) -> Membership:
    """Replace a faculty member's grants (B-09), refusing stale changes (If-Match).

    The new grants apply from the member's next request: permissions are reloaded every time.
    Sending the grants they already have changes nothing.
    """
    require(principal, Action.MANAGE_FACULTY)
    member = get_member(session, membership_id, lock=True)
    require_if_match(if_match, member.revision)
    if member.status != "ACTIVE":
        raise Conflict("This person is no longer a member.", code="MEMBER_REMOVED")
    if member.role != "FACULTY":
        raise Conflict(
            "Only faculty have grants; the Owner and admins already hold all of them.",
            code="NOT_FACULTY",
        )
    current = {
        Grant(name)
        for name in session.scalars(
            select(MembershipGrant.grant_name).where(MembershipGrant.membership_id == member.id)
        )
    }
    if grants == current:
        return member
    for grant in current - grants:
        session.execute(
            delete(MembershipGrant).where(
                MembershipGrant.membership_id == member.id, MembershipGrant.grant_name == grant
            )
        )
    for grant in sorted(grants - current):
        session.add(
            MembershipGrant(
                organization_id=member.organization_id,
                membership_id=member.id,
                grant_name=grant,
                granted_by=principal.user_id,
            )
        )
    member.revision += 1
    member.updated_at = datetime.now(UTC)
    session.flush()
    record_event(
        session,
        action="MEMBER_GRANTS_CHANGED",
        entity_type="membership",
        entity_id=member.id,
        organization_id=member.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_is_platform(principal),
        request_id=request_id,
        before={"grants": sorted(current)},
        after={"grants": sorted(grants)},
    )
    return member
