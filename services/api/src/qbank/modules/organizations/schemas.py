from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, EmailStr, Field, StringConstraints, model_validator

from qbank.core.pagination import PageInfo
from qbank.core.permissions import Grant

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


class UpdateOrganization(BaseModel):
    """Only the fields sent are changed."""

    display_name: Name | None = None
    timezone: TimeZone | None = None

    @model_validator(mode="after")
    def _something_to_change(self) -> UpdateOrganization:
        if self.display_name is None and self.timezone is None:
            raise ValueError("Send display_name, timezone or both.")
        return self


class ActIn(BaseModel):
    organization_id: UUID


# --- Members (M2 PR 5) ----------------------------------------------------------------------------


class MemberOut(BaseModel):
    membership_id: UUID
    user_id: UUID
    display_name: str
    email: str | None = Field(description="Sign-in email; null only for an account without one")
    role: str = Field(description="OWNER, ADMIN or FACULTY")
    status: str = Field(description="Membership: ACTIVE or REMOVED")
    account_status: str = Field(description="INVITED (not activated yet), ACTIVE or DISABLED")
    grants: list[str] = Field(description="Faculty grants (Owner and admins hold all implicitly)")
    revision: int
    joined_at: datetime
    actions: list[str] = Field(
        description=(
            "What you may do to this member now: NEW_ACTIVATION_LINK, NEW_RESET_LINK, SET_GRANTS."
            " The web app shows only these buttons; the API checks again on every request."
        )
    )


class MemberPage(BaseModel):
    data: list[MemberOut]
    page: PageInfo


class InviteMember(BaseModel):
    email: EmailStr
    display_name: Name
    role: Literal["ADMIN", "FACULTY"] = Field(
        description="The Owner is created with the coaching and changes only by a transfer."
    )


class InvitedMember(BaseModel):
    member: MemberOut
    activation: ActivationLink | None = Field(
        description=(
            "The invitee's activation link. Null only when a retried request finds that they"
            " have already activated their account."
        )
    )


class AccountLinkOut(BaseModel):
    token: str = Field(
        description=(
            "Shown only now. The web app turns it into `<app address>/activate#<token>`. Any"
            " earlier link of the same kind for this member stops working."
        )
    )
    expires_at: datetime


class SetGrants(BaseModel):
    grants: list[Grant] = Field(
        max_length=len(Grant),
        description="The complete new set (an empty list removes all); repeats count once.",
        examples=[["QC", "APPROVE"]],
    )
