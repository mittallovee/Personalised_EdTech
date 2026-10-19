from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class MyOrganization(BaseModel):
    id: UUID
    role: str


class Me(BaseModel):
    id: UUID
    display_name: str
    is_platform_admin: bool
    organization: MyOrganization | None
    acting_organization_id: UUID | None


class LoginResponse(BaseModel):
    user: Me
    csrf_token: str = Field(description="Send back in the X-CSRF-Token header on changes.")
