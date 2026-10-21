from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.errors import NotFound
from qbank.core.etag import IfMatchHeader, etag
from qbank.core.idempotency import IdempotencyKeyHeader
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.core.permissions import Action, require
from qbank.core.tenancy import TenantContext
from qbank.modules.organizations import service
from qbank.modules.organizations.models import Organization
from qbank.modules.organizations.schemas import (
    ActIn,
    ActivationLink,
    CreatedOrganization,
    CreateOrganization,
    InvitedOwner,
    OrganizationOut,
    OrganizationPage,
    UpdateOrganization,
)

router = APIRouter(prefix="/api/v1/platform", tags=["platform"])

_PLATFORM_ONLY: dict[int | str, dict[str, Any]] = {
    403: {"description": "Only platform admins may do this (`PERMISSION_DENIED`)"}
}


def to_out(organization: Organization) -> OrganizationOut:
    return OrganizationOut(
        id=organization.id,
        display_name=organization.display_name,
        status=organization.status,
        timezone=organization.timezone,
        revision=organization.revision,
        created_at=organization.created_at,
    )


@router.post(
    "/organizations",
    status_code=status.HTTP_201_CREATED,
    summary="Create a coaching and invite its first Owner (A-04)",
    description=(
        "Creates the coaching, the Owner's account (invited: it cannot sign in yet) and a one-time"
        " activation link valid for 24 hours. Send an `Idempotency-Key` so a retry after a lost"
        " response returns the same coaching (with a fresh link) instead of failing."
    ),
    responses={
        **_PLATFORM_ONLY,
        409: {
            "description": "The Owner's email already has an account (`EMAIL_TAKEN`), or the"
            " Idempotency-Key was used for a different request (`IDEMPOTENCY_KEY_REUSED`)"
        },
    },
)
def create_organization(
    body: CreateOrganization,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    idempotency_key: Annotated[str | None, IdempotencyKeyHeader] = None,
) -> CreatedOrganization:
    require(principal, Action.MANAGE_COACHINGS)
    with database.transaction(
        TenantContext(user_id=principal.user_id, is_platform=True)
    ) as session:
        organization, owner, link = service.create_organization(
            session,
            principal,
            body,
            idempotency_key=idempotency_key,
            request_id=request.state.request_id,
        )
        result = CreatedOrganization(
            organization=to_out(organization),
            owner=InvitedOwner(
                user_id=owner.user_id,
                membership_id=owner.id,
                display_name=body.owner.display_name,
                email=body.owner.email.strip().lower(),
            ),
            activation=ActivationLink(token=link.token, expires_at=link.expires_at)
            if link
            else None,
        )
    response.headers["Location"] = f"/api/v1/platform/organizations/{organization.id}"
    response.headers["Cache-Control"] = "no-store"  # the response carries a secret link token
    return result


@router.get(
    "/organizations",
    summary="All coachings, newest first",
    responses=_PLATFORM_ONLY,
)
def list_organizations(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> OrganizationPage:
    require(principal, Action.MANAGE_COACHINGS)
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(
        TenantContext(user_id=principal.user_id, is_platform=True)
    ) as session:
        rows, has_more = service.list_organizations(session, limit=limit, after=after)
        data = [to_out(row) for row in rows]
    next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id) if has_more else None
    return OrganizationPage(data=data, page=PageInfo(next_cursor=next_cursor, has_more=has_more))


@router.get(
    "/organizations/{organization_id}",
    summary="One coaching",
    responses={**_PLATFORM_ONLY, 404: {"description": "No such coaching (`NOT_FOUND`)"}},
)
def get_organization(
    organization_id: UUID,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> OrganizationOut:
    require(principal, Action.MANAGE_COACHINGS)
    with database.transaction(_platform(principal)) as session:
        organization = session.get(Organization, organization_id)
        if organization is None:
            raise NotFound("No such coaching.")
        response.headers["ETag"] = etag(organization.revision)
        return to_out(organization)


_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such coaching (`NOT_FOUND`)"}
}
_STALE: dict[int | str, dict[str, Any]] = {
    412: {"description": "Changed by someone else since your read (`REVISION_STALE`)"},
    428: {"description": "The If-Match header is missing (`IF_MATCH_REQUIRED`)"},
}


@router.patch(
    "/organizations/{organization_id}",
    summary="Rename a coaching or change its time zone",
    description="Send the ETag from your last read in `If-Match`. Only the fields sent change.",
    responses={**_PLATFORM_ONLY, **_NOT_FOUND, **_STALE},
)
def update_organization(
    organization_id: UUID,
    body: UpdateOrganization,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> OrganizationOut:
    require(principal, Action.MANAGE_COACHINGS)
    with database.transaction(_platform(principal)) as session:
        organization = service.update_organization(
            session,
            principal,
            organization_id,
            body,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(organization.revision)
        return to_out(organization)


def _set_status(
    organization_id: UUID,
    new_status: str,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Database,
) -> OrganizationOut:
    require(principal, Action.MANAGE_COACHINGS)
    with database.transaction(_platform(principal)) as session:
        organization = service.set_status(
            session, principal, organization_id, new_status, request_id=request.state.request_id
        )
        response.headers["ETag"] = etag(organization.revision)
        return to_out(organization)


@router.post(
    "/organizations/{organization_id}/suspend",
    summary="Suspend a coaching (A-07)",
    description=(
        "Its members are signed out on their next request and cannot sign in; its data is kept."
        " Suspending a suspended coaching changes nothing."
    ),
    responses={**_PLATFORM_ONLY, **_NOT_FOUND},
)
def suspend_organization(
    organization_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> OrganizationOut:
    return _set_status(organization_id, "SUSPENDED", principal, request, response, database)


@router.post(
    "/organizations/{organization_id}/reactivate",
    summary="Reactivate a suspended coaching",
    responses={**_PLATFORM_ONLY, **_NOT_FOUND},
)
def reactivate_organization(
    organization_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> OrganizationOut:
    return _set_status(organization_id, "ACTIVE", principal, request, response, database)


@router.post(
    "/acting-organization",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Act inside a coaching (A-06)",
    description=(
        "Until stopped or signed out, this sign-in session works inside that coaching with full"
        " authority. Changes are audited as made by a platform admin, and starting and stopping"
        " appear in the coaching's audit log. `/me` shows the coaching acted in."
    ),
    responses={**_PLATFORM_ONLY, **_NOT_FOUND},
)
def start_acting(
    body: ActIn,
    principal: CurrentPrincipal,
    request: Request,
    database: Annotated[Database, Depends(get_database)],
) -> None:
    require(principal, Action.MANAGE_COACHINGS)
    with database.transaction(_platform(principal)) as session:
        service.act_in(
            session, principal, body.organization_id, request_id=request.state.request_id
        )


@router.delete(
    "/acting-organization",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop acting inside a coaching",
    responses=_PLATFORM_ONLY,
)
def stop_acting(
    principal: CurrentPrincipal,
    request: Request,
    database: Annotated[Database, Depends(get_database)],
) -> None:
    require(principal, Action.MANAGE_COACHINGS)
    with database.transaction(_platform(principal)) as session:
        service.act_in(session, principal, None, request_id=request.state.request_id)


def _platform(principal: CurrentPrincipal) -> TenantContext:
    return TenantContext(user_id=principal.user_id, is_platform=True)
