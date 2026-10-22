from typing import Literal
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


class AuthMethods(BaseModel):
    password: bool = Field(description="Sign-in with email and password is always available.")
    google: bool = Field(description="Google sign-in is set up on this server; show its button.")


class GoogleStartRequest(BaseModel):
    purpose: Literal["SIGN_IN"] = Field(description="What the person is doing at Google.")
    return_origin: str = Field(
        max_length=200,
        description="The web address the person is on; must be one of ALLOWED_ORIGINS.",
        examples=["http://localhost:3000"],
    )


class GoogleActivationStartRequest(BaseModel):
    return_origin: str = Field(
        max_length=200,
        description="The web address the person is on; must be one of ALLOWED_ORIGINS.",
        examples=["http://localhost:3000"],
    )
    link_token: str = Field(
        min_length=20, max_length=100, description="The part after # in the activation link."
    )


class GoogleStartResponse(BaseModel):
    authorization_url: str = Field(description="Send the person's browser here.")


class GoogleLinkStartRequest(BaseModel):
    return_origin: str = Field(
        max_length=200,
        description="The web address the person is on; must be one of ALLOWED_ORIGINS.",
        examples=["http://localhost:3000"],
    )
    password: str = Field(
        min_length=1,
        max_length=128,
        description="The account's current password: a session alone never links Google.",
    )


class GoogleStatus(BaseModel):
    linked: bool
    email: str | None = Field(description="The Google account's email when it was linked.")


class LoginMethods(BaseModel):
    password: bool = Field(description="The account has a password.")
    google: GoogleStatus
