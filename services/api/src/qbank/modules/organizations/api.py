from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.errors import NotFound
from qbank.core.idempotency import IdempotencyKeyHeader
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.core.permissions import Action, require
from qbank.core.tenancy import TenantContext
from qbank.modules.organizations import service
from qbank.modules.organizations.models import Organization
from qbank.modules.organizations.schemas import (
    ActivationLink,
    CreatedOrganization,
    CreateOrganization,
    InvitedOwner,
    OrganizationOut,
    OrganizationPage,
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
    database: Annotated[Database, Depends(get_database)],
) -> OrganizationOut:
    require(principal, Action.MANAGE_COACHINGS)
    with database.transaction(
        TenantContext(user_id=principal.user_id, is_platform=True)
    ) as session:
        organization = session.get(Organization, organization_id)
        if organization is None:
            raise NotFound("No such coaching.")
        return to_out(organization)
