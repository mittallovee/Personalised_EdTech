from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from qbank.core.auth import SESSION_COOKIE, CurrentPrincipal, Principal
from qbank.core.clientip import client_address
from qbank.core.config import Settings
from qbank.core.db import Database, get_database
from qbank.core.errors import TooManyRequests
from qbank.core.metrics import RATE_LIMITED
from qbank.core.permissions import Grant, has_grant
from qbank.core.ratelimit import LoginRateLimiter
from qbank.core.security import hash_token
from qbank.modules.identity import service
from qbank.modules.identity.authenticator import CSRF_COOKIE
from qbank.modules.identity.schemas import (
    LoginRequest,
    LoginResponse,
    Me,
    MyOrganization,
    RedeemLinkRequest,
)

router = APIRouter(prefix="/api/v1", tags=["identity"])


def get_settings_from_app(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def to_me(principal: Principal) -> Me:
    organization = None
    if principal.organization_id is not None and principal.role is not None:
        organization = MyOrganization(
            id=principal.organization_id,
            display_name=principal.organization_name or "",
            role=principal.role,
            grants=sorted(grant for grant in Grant if has_grant(principal, grant)),
        )
    return Me(
        id=principal.user_id,
        display_name=principal.display_name,
        is_platform_admin=principal.is_platform_admin,
        organization=organization,
        acting_organization_id=principal.acting_organization_id,
        acting_organization_name=principal.acting_organization_name,
    )


def set_auth_cookies(response: Response, settings: Settings, result: service.LoginResult) -> None:
    """Session cookie: HttpOnly (scripts cannot read it). CSRF cookie: readable by our web app.

    SameSite=Lax keeps the cookies off cross-site sub-requests while normal links into the app still
    work; the CSRF token is the real protection for changes.
    """
    max_age = settings.session_absolute_days * 24 * 60 * 60
    for name, value, http_only in (
        (SESSION_COOKIE, result.session_token, True),
        (CSRF_COOKIE, result.csrf_token, False),
    ):
        response.set_cookie(
            name,
            value,
            max_age=max_age,
            httponly=http_only,
            secure=settings.session_cookie_secure,
            samesite="lax",
            path="/",
        )


@router.post(
    "/auth/login",
    summary="Sign in with email and password",
    responses={
        401: {"description": "Email or password is incorrect (one message for all cases)"},
        429: {"description": "Too many attempts; see the Retry-After header"},
    },
)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> LoginResponse:
    limiter: LoginRateLimiter = request.app.state.login_limiter
    client_ip = client_address(request)
    wait = limiter.check(client_ip, body.email)
    if wait:
        RATE_LIMITED.labels("login").inc()
        raise TooManyRequests(
            "Too many sign-in attempts. Please wait and try again.", retry_after_seconds=wait
        )
    result = service.login(database, settings, body.email, body.password, request.state.request_id)
    set_auth_cookies(response, settings, result)
    return LoginResponse(user=to_me(result.principal), csrf_token=result.csrf_token)


@router.post(
    "/auth/links/redeem",
    summary="Activate an account or reset its password with a one-time link",
    description=(
        "For people who are not signed in (no session or CSRF token needed): the token from the"
        " link and a new password. On success the person is signed in, exactly as after"
        " `POST /auth/login`. A reset ends all their other sessions. Rate-limited like sign-in."
    ),
    responses={
        401: {
            "description": "The link is unknown, used, replaced, expired, or its membership or"
            " coaching is no longer active (`LINK_INVALID`, one message for all cases)"
        },
        429: {"description": "Too many attempts; see the Retry-After header"},
    },
)
def redeem_link(
    body: RedeemLinkRequest,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> LoginResponse:
    limiter: LoginRateLimiter = request.app.state.login_limiter
    # Counted per client address and per link, like sign-in counts per address and per email.
    wait = limiter.check(client_address(request), f"link:{hash_token(body.token)}")
    if wait:
        RATE_LIMITED.labels("link").inc()
        raise TooManyRequests(
            "Too many attempts. Please wait and try again.", retry_after_seconds=wait
        )
    result = service.redeem_link(
        database, settings, body.token, body.password, request.state.request_id
    )
    set_auth_cookies(response, settings, result)
    return LoginResponse(user=to_me(result.principal), csrf_token=result.csrf_token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
def logout(
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> None:
    service.logout(database, principal, request.state.request_id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


@router.get("/me", summary="The signed-in user")
def me(principal: CurrentPrincipal) -> Me:
    return to_me(principal)
