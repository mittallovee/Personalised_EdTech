from typing import Annotated

from fastapi import APIRouter, Depends, Request

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader
from qbank.modules.organizations import members
from qbank.modules.organizations.schemas import OwnershipTransferred, TransferOwnership

router = APIRouter(prefix="/api/v1/organization", tags=["members"])


@router.post(
    "/transfer-ownership",
    summary="Hand the coaching to another admin (B-08)",
    description=(
        "The Owner (or a platform admin acting in the coaching) makes an admin of this coaching"
        " the Owner; the old Owner becomes an admin. Name the Owner you saw in"
        " `expected_owner_membership_id` and send that Owner's ETag (from `GET /members/{id}`)"
        " in `If-Match`; if either is out of date nothing changes. The new Owner must be an"
        " admin who has activated their account. The change applies from each person's next"
        " request."
    ),
    responses={
        403: {"description": "Only the Owner may do this (`PERMISSION_DENIED`)"},
        404: {"description": "No such member in your coaching (`NOT_FOUND`)"},
        409: {
            "description": "The Owner is someone else now (`OWNER_CHANGED`), or the new Owner is"
            " not an active admin (`INVALID_NEW_OWNER`)"
        },
        412: {"description": "Changed by someone else since your read (`REVISION_STALE`)"},
        428: {"description": "The If-Match header is missing (`IF_MATCH_REQUIRED`)"},
    },
)
def transfer_ownership(
    body: TransferOwnership,
    principal: CurrentPrincipal,
    request: Request,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> OwnershipTransferred:
    with database.transaction(principal.tenant_context) as session:
        previous, new = members.transfer_ownership(
            session, principal, body, if_match=if_match, request_id=request.state.request_id
        )
        previous_out, new_out = members.describe(session, principal, [previous, new])
    return OwnershipTransferred(previous_owner=previous_out, new_owner=new_out)
