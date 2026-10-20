from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from qbank.core.pagination import PageInfo


class AuditActor(BaseModel):
    user_id: UUID | None
    display_name: str | None = Field(
        description="Null when the person is not visible here, e.g. a platform admin."
    )
    is_platform_admin: bool = Field(description="The change was made with platform authority.")


class AuditEventOut(BaseModel):
    id: UUID
    created_at: datetime
    action: str = Field(examples=["USER_SIGNED_OUT"])
    entity_type: str
    entity_id: UUID | None
    actor: AuditActor
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    request_id: str | None


class AuditEventPage(BaseModel):
    data: list[AuditEventOut]
    page: PageInfo
