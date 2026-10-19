"""Who is calling: the ``Principal`` and pluggable authenticators (ADR-0006).

Business code depends only on ``require_principal`` and never reads cookies or tokens. Each way of
signing in (session cookie now, OAuth bearer tokens for mobile apps later) is an ``Authenticator``
registered in ``create_app``.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyCookie

from qbank.core.errors import Unauthenticated
from qbank.core.tenancy import TenantContext

# How the web app signs in (style guide §7). Part of the API contract, so defined here.
SESSION_COOKIE = "qb_session"
CSRF_HEADER = "X-CSRF-Token"

# Declares the cookie in the OpenAPI contract; reading and checking it is the authenticators' job.
_session_cookie = APIKeyCookie(
    name=SESSION_COOKIE,
    scheme_name="sessionCookie",
    description="Session cookie set by POST /api/v1/auth/login (HttpOnly; the browser sends it).",
    auto_error=False,
)


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: UUID
    display_name: str
    is_platform_admin: bool
    organization_id: UUID | None  # the user's own coaching (None for a platform-only admin)
    role: str | None  # OWNER / ADMIN / FACULTY in that coaching
    session_id: UUID | None = None
    acting_organization_id: UUID | None = None  # platform admin working inside a coaching

    @property
    def tenant_context(self) -> TenantContext:
        return TenantContext(
            organization_id=self.acting_organization_id or self.organization_id,
            user_id=self.user_id,
            is_platform=self.is_platform_admin,
        )


class Authenticator(Protocol):
    def authenticate(self, request: Request) -> Principal | None:
        """Return the caller, or None if this method does not apply / credentials are invalid."""
        ...


def get_optional_principal(request: Request) -> Principal | None:
    if hasattr(request.state, "principal"):
        cached: Principal | None = request.state.principal
        return cached
    authenticators: Sequence[Authenticator] = request.app.state.authenticators
    principal = None
    for authenticator in authenticators:
        principal = authenticator.authenticate(request)
        if principal is not None:
            break
    request.state.principal = principal
    return principal


def require_principal(
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
    _contract: Annotated[str | None, Security(_session_cookie)] = None,
) -> Principal:
    if principal is None:
        raise Unauthenticated("Please sign in.")
    return principal


CurrentPrincipal = Annotated[Principal, Depends(require_principal)]
