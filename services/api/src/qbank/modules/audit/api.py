from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo, decode_cursor, encode_cursor
from qbank.core.permissions import Action, require
from qbank.modules.audit import service
from qbank.modules.audit.schemas import AuditActor, AuditEventOut, AuditEventPage
from qbank.modules.identity.public import display_names

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get(
    "/audit-events",
    summary="Audit log: who changed what, and when (I-03)",
    description=(
        "Owner and admins see their coaching's events. A platform admin sees the coaching they act"
        " in, or platform-level events when not acting in one. Newest first."
    ),
    responses={403: {"description": "Only the Owner and admins may read it (`PERMISSION_DENIED`)"}},
)
def list_audit_events(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
    entity_type: Annotated[str | None, Query(max_length=100)] = None,
    entity_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    since: Annotated[
        AwareDatetime | None, Query(description="Events at or after this time (with time zone).")
    ] = None,
    until: Annotated[
        AwareDatetime | None, Query(description="Events before this time (with time zone).")
    ] = None,
) -> AuditEventPage:
    require(principal, Action.VIEW_AUDIT_LOG)
    after = decode_cursor(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
        rows, has_more = service.list_events(
            session,
            organization_id=principal.tenant_context.organization_id,
            limit=limit,
            after=after,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            since=since,
            until=until,
        )
        names = display_names(session, {row.actor_user_id for row in rows if row.actor_user_id})
        events = [
            AuditEventOut(
                id=row.id,
                created_at=row.created_at,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                actor=AuditActor(
                    user_id=row.actor_user_id,
                    display_name=names.get(row.actor_user_id) if row.actor_user_id else None,
                    is_platform_admin=row.actor_is_platform,
                ),
                before=row.before,
                after=row.after,
                request_id=row.request_id,
            )
            for row in rows
        ]
    next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id) if has_more else None
    return AuditEventPage(data=events, page=PageInfo(next_cursor=next_cursor, has_more=has_more))
