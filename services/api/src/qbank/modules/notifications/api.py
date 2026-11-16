from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from qbank.core.auth import CurrentPrincipal, Principal
from qbank.core.db import Database, get_database
from qbank.core.errors import PermissionDenied
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.core.permissions import Action, require
from qbank.core.tenancy import TenantContext
from qbank.modules.notifications import service
from qbank.modules.notifications.models import Notification
from qbank.modules.notifications.schemas import (
    MarkedRead,
    NotificationOut,
    NotificationPage,
    UnreadCount,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

_OWN = "A person sees and marks only their own notifications; another person's is not found."


def _scope(principal: Principal) -> tuple[TenantContext, UUID]:
    """The coaching this person is working in. Everyone allowed the action has one."""
    context = principal.tenant_context
    if context.organization_id is None:
        raise PermissionDenied("You don't have permission to do this.")
    return context, context.organization_id


def _out(row: Notification) -> NotificationOut:
    return NotificationOut(
        id=row.id, kind=row.kind, data=row.data, created_at=row.created_at, read_at=row.read_at
    )


@router.get(
    "",
    summary="Your notifications, newest first (I-01)",
    description=f"The screen reads this on load and about once a minute. {_OWN}",
)
def list_notifications(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    unread: Annotated[bool, Query(description="Only the ones not yet read.")] = False,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> NotificationPage:
    require(principal, Action.USE_NOTIFICATIONS)
    after = decode_cursor(cursor) if cursor is not None else None
    context, org = _scope(principal)
    with database.transaction(context) as session:
        rows, has_more = service.list_notifications(
            session,
            user_id=principal.user_id,
            organization_id=org,
            unread_only=unread,
            limit=limit,
            after=after,
        )
        data = [_out(row) for row in rows]
        next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id) if has_more else None
    return NotificationPage(data=data, page=PageInfo(next_cursor=next_cursor, has_more=has_more))


@router.get(
    "/unread-count",
    summary="How many notifications you have not read (the bell)",
    description=_OWN,
)
def unread_count(
    principal: CurrentPrincipal, database: Annotated[Database, Depends(get_database)]
) -> UnreadCount:
    require(principal, Action.USE_NOTIFICATIONS)
    context, org = _scope(principal)
    with database.transaction(context) as session:
        count = service.unread_count(session, user_id=principal.user_id, organization_id=org)
    return UnreadCount(count=count)


@router.post(
    "/read-all",
    summary="Mark all your notifications as read",
    description="Safe to repeat: a second call marks nothing and answers `updated: 0`.",
)
def read_all(
    principal: CurrentPrincipal, database: Annotated[Database, Depends(get_database)]
) -> MarkedRead:
    require(principal, Action.USE_NOTIFICATIONS)
    context, org = _scope(principal)
    with database.transaction(context) as session:
        updated = service.mark_all_read(session, user_id=principal.user_id, organization_id=org)
    return MarkedRead(updated=updated)


@router.post(
    "/{notification_id}/read",
    summary="Mark one notification as read",
    description=f"Safe to repeat: the first read time stays. {_OWN}",
    responses={404: {"description": "Not yours, or it does not exist (`NOT_FOUND`)"}},
)
def read_one(
    notification_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> NotificationOut:
    require(principal, Action.USE_NOTIFICATIONS)
    context, org = _scope(principal)
    with database.transaction(context) as session:
        row = service.mark_read(
            session,
            user_id=principal.user_id,
            organization_id=org,
            notification_id=notification_id,
        )
        return _out(row)
