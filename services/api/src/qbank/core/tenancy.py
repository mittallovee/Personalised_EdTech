"""Tenant (coaching) context for database transactions (ADR-0005).

Row-level-security policies read these transaction-local settings:
- ``app.org_id``      the coaching the request acts in (empty = none → tenant tables return no rows)
- ``app.user_id``     the signed-in user (lets users see their own record)
- ``app.is_platform`` "true" only for a verified platform admin
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True, slots=True)
class TenantContext:
    organization_id: UUID | None = None
    user_id: UUID | None = None
    is_platform: bool = False


NO_CONTEXT = TenantContext()

_APPLY_CONTEXT = text(
    "SELECT set_config('app.org_id', :org_id, true),"
    " set_config('app.user_id', :user_id, true),"
    " set_config('app.is_platform', :is_platform, true)"
)


def apply_tenant_context(session: Session, context: TenantContext) -> None:
    """Set the context for the current transaction only (``is_local``), using bound values."""
    session.execute(
        _APPLY_CONTEXT,
        {
            "org_id": str(context.organization_id) if context.organization_id else "",
            "user_id": str(context.user_id) if context.user_id else "",
            "is_platform": "true" if context.is_platform else "false",
        },
    )
