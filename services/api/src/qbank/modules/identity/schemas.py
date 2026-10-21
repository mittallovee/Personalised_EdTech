from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MyOrganization(BaseModel):
    id: UUID
    display_name: str
    role: str
    grants: list[str] = Field(
        description="Grants in effect (Owner and admins hold all of them), sorted by name."
    )


class Me(BaseModel):
    id: UUID
    display_name: str
    is_platform_admin: bool
    organization: MyOrganization | None
    acting_organization_id: UUID | None
    acting_organization_name: str | None = Field(
        default=None, description="Name of the coaching a platform admin is acting in."
    )


class LoginResponse(BaseModel):
    user: Me
    csrf_token: str = Field(description="Send back in the X-CSRF-Token header on changes.")


class RedeemLinkRequest(BaseModel):
    token: str = Field(min_length=20, max_length=100, description="The part after # in the link.")
    password: str = Field(
        min_length=12, max_length=128, description="The new password (at least 12 characters)."
    )
