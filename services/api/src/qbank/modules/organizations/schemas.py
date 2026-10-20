from datetime import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints

from qbank.core.pagination import PageInfo

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def _known_timezone(name: str) -> str:
    try:
        ZoneInfo(name)
    except ZoneInfoNotFoundError, ValueError:
        raise ValueError("Use a time zone name such as Asia/Kolkata.") from None
    return name


TimeZone = Annotated[str, Field(max_length=64), AfterValidator(_known_timezone)]


class NewOwner(BaseModel):
    email: EmailStr
    display_name: Name


class CreateOrganization(BaseModel):
    display_name: Name = Field(examples=["Sharma Classes"])
    timezone: TimeZone = "Asia/Kolkata"
    owner: NewOwner


class OrganizationOut(BaseModel):
    id: UUID
    display_name: str
    status: str = Field(description="ACTIVE or SUSPENDED")
    timezone: str
    revision: int
    created_at: datetime


class OrganizationPage(BaseModel):
    data: list[OrganizationOut]
    page: PageInfo


class InvitedOwner(BaseModel):
    user_id: UUID
    membership_id: UUID
    display_name: str
    email: str


class ActivationLink(BaseModel):
    token: str = Field(
        description="Shown only now. The web app turns it into `<app address>/activate#<token>`."
    )
    expires_at: datetime


class CreatedOrganization(BaseModel):
    organization: OrganizationOut
    owner: InvitedOwner
    activation: ActivationLink | None = Field(
        description=(
            "A new activation link for the Owner. Null only when a retried request finds that the"
            " Owner has already activated their account."
        )
    )
