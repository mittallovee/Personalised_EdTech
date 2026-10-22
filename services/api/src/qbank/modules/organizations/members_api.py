from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.core.idempotency import IdempotencyKeyHeader
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.core.permissions import Action, require
from qbank.modules.identity.public import LinkPurpose
from qbank.modules.organizations import members
from qbank.modules.organizations.schemas import (
    AccountLinkOut,
    ActivationLink,
    ChangeRole,
    InvitedMember,
    InviteMember,
    MemberOut,
    MemberPage,
    RemoveMember,
    SetGrants,
)

router = APIRouter(prefix="/api/v1/members", tags=["members"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such member in your coaching (`NOT_FOUND`)"}
}


@router.get(
    "",
    summary="Members of your coaching, newest first",
    description="Owner and admins (and a platform admin acting in the coaching). Removed members"
    " are left out.",
    responses=_DENIED,
)
def list_members(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> MemberPage:
    require(principal, Action.VIEW_MEMBERS)
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
        rows, has_more = members.list_members(session, principal, limit=limit, after=after)
        data = members.describe(session, principal, rows)
    next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id) if has_more else None
    return MemberPage(data=data, page=PageInfo(next_cursor=next_cursor, has_more=has_more))


@router.get(
    "/{membership_id}",
    summary="One member",
    description="The ETag is the member's revision, for changes that need `If-Match`.",
    responses={**_DENIED, **_NOT_FOUND},
)
def get_member(
    membership_id: UUID,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> MemberOut:
    require(principal, Action.VIEW_MEMBERS)
    with database.transaction(principal.tenant_context) as session:
        member = members.get_member(session, membership_id)
        response.headers["ETag"] = etag(member.revision)
        return members.describe(session, principal, [member])[0]


@router.post(
    "/invitations",
    status_code=status.HTTP_201_CREATED,
    summary="Invite an admin or faculty member (B-05)",
    description=(
        "Creates their account (invited: it cannot sign in yet) and a one-time activation link"
        " valid for 24 hours, for you to send them. Admins invite faculty; only the Owner invites"
        " admins. Send an `Idempotency-Key` so a retry after a lost response returns the same"
        " member (with a fresh link) instead of failing."
    ),
    responses={
        **_DENIED,
        409: {
            "description": "The email already has an account, in any coaching (`EMAIL_TAKEN`),"
            " or the Idempotency-Key was used for a different request (`IDEMPOTENCY_KEY_REUSED`)"
        },
    },
)
def invite_member(
    body: InviteMember,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    idempotency_key: Annotated[str | None, IdempotencyKeyHeader] = None,
) -> InvitedMember:
    with database.transaction(principal.tenant_context) as session:
        member, link = members.invite_member(
            session,
            principal,
            body,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )
        result = InvitedMember(
            member=members.describe(session, principal, [member])[0],
            activation=ActivationLink(token=link.token, expires_at=link.expires_at)
            if link
            else None,
        )
    response.headers["Location"] = f"/api/v1/members/{member.id}"
    response.headers["Cache-Control"] = "no-store"  # the response carries a secret link token
    return result


_LINK_CONFLICTS: dict[int | str, dict[str, Any]] = {
    409: {
        "description": "Wrong kind of link for this account (`ALREADY_ACTIVATED` or"
        " `NOT_ACTIVATED`), the account is disabled (`ACCOUNT_DISABLED`), or they are no longer"
        " a member (`MEMBER_REMOVED`)"
    }
}


def _new_link(
    membership_id: UUID,
    purpose: LinkPurpose,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Database,
) -> AccountLinkOut:
    with database.transaction(principal.tenant_context) as session:
        link = members.new_link(
            session, principal, membership_id, purpose, request_id=request.state.request_id
        )
    response.headers["Cache-Control"] = "no-store"
    return AccountLinkOut(token=link.token, expires_at=link.expires_at)


@router.post(
    "/{membership_id}/activation-link",
    summary="New activation link for someone who has not activated yet",
    description="Valid for 24 hours; their earlier activation link stops working.",
    responses={**_DENIED, **_NOT_FOUND, **_LINK_CONFLICTS},
)
def new_activation_link(
    membership_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> AccountLinkOut:
    return _new_link(membership_id, LinkPurpose.ACTIVATION, principal, request, response, database)


@router.post(
    "/{membership_id}/reset-link",
    summary="Password-reset link for an active account",
    description=(
        "Valid for 1 hour; using it sets a new password and signs the person out everywhere"
        " else. Admins make links for faculty, the Owner for admins too; the Owner's own link"
        " comes from a platform admin."
    ),
    responses={**_DENIED, **_NOT_FOUND, **_LINK_CONFLICTS},
)
def new_reset_link(
    membership_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> AccountLinkOut:
    return _new_link(membership_id, LinkPurpose.RESET, principal, request, response, database)


@router.put(
    "/{membership_id}/grants",
    summary="Set a faculty member's grants (B-09)",
    description=(
        "Replaces their grants with the list sent (QC, APPROVE, PUBLISH, EDIT_OTHERS,"
        " MANAGE_AI_PROMPTS). Owner and admins may do this. Send the ETag from your last read"
        " in `If-Match`. The change applies from the member's next request."
    ),
    responses={
        **_DENIED,
        **_NOT_FOUND,
        409: {
            "description": "The member is not faculty (`NOT_FACULTY`), or no longer a member"
            " (`MEMBER_REMOVED`)"
        },
        412: {"description": "Changed by someone else since your read (`REVISION_STALE`)"},
        428: {"description": "The If-Match header is missing (`IF_MATCH_REQUIRED`)"},
    },
)
def set_grants(
    membership_id: UUID,
    body: SetGrants,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> MemberOut:
    with database.transaction(principal.tenant_context) as session:
        member = members.set_grants(
            session,
            principal,
            membership_id,
            set(body.grants),
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(member.revision)
        return members.describe(session, principal, [member])[0]


_CHANGE_ERRORS: dict[int | str, dict[str, Any]] = {
    **_DENIED,
    **_NOT_FOUND,
    409: {
        "description": "The person was already removed (`MEMBER_REMOVED`), their role is not"
        " the one you named (`ROLE_CHANGED`), or they are the Owner (`LAST_OWNER`)"
    },
    412: {"description": "Changed by someone else since your read (`REVISION_STALE`)"},
    428: {"description": "The If-Match header is missing (`IF_MATCH_REQUIRED`)"},
}


@router.post(
    "/{membership_id}/change-role",
    summary="Promote faculty to admin, or demote an admin to faculty (B-08)",
    description=(
        "Owner only. Name the role you saw in `expected_role` and send the ETag from your last"
        " read in `If-Match`; if either is out of date nothing changes. Their grants are cleared"
        " (admins hold every grant anyway). The new role applies from their next request. The"
        " Owner changes only by a transfer of ownership."
    ),
    responses=_CHANGE_ERRORS,
)
def change_role(
    membership_id: UUID,
    body: ChangeRole,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> MemberOut:
    with database.transaction(principal.tenant_context) as session:
        member = members.change_role(
            session,
            principal,
            membership_id,
            body,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(member.revision)
        return members.describe(session, principal, [member])[0]


@router.post(
    "/{membership_id}/remove",
    summary="Remove someone from the coaching (B-08, B-09, B-10)",
    description=(
        "Owner and admins remove faculty; only the Owner removes admins. Their sign-in sessions"
        " and unused links end at once; their content and history stay with the coaching. If they"
        " never activated, their email is freed. Name the role you saw in `expected_role` and send"
        " the ETag in `If-Match`. The Owner can't be removed."
    ),
    responses=_CHANGE_ERRORS,
)
def remove_member(
    membership_id: UUID,
    body: RemoveMember,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> MemberOut:
    with database.transaction(principal.tenant_context) as session:
        member = members.remove_member(
            session,
            principal,
            membership_id,
            body,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(member.revision)
        return members.describe(session, principal, [member])[0]
