from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from qbank.core.pagination import PageInfo


class NotificationOut(BaseModel):
    id: UUID
    kind: str = Field(examples=["REVIEW_RETURNED", "QUESTION_PUBLISHED"])
    data: dict[str, Any] = Field(
        description="Ids and short facts (the question code, the reasons). Show as text only."
    )
    created_at: datetime
    read_at: datetime | None = Field(description="Null while unread.")


class NotificationPage(BaseModel):
    data: list[NotificationOut]
    page: PageInfo


class UnreadCount(BaseModel):
    count: int = Field(ge=0)


class MarkedRead(BaseModel):
    updated: int = Field(ge=0, description="How many unread notifications were marked as read.")
