from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse

from qbank.core.auth import CurrentPrincipal
from qbank.core.clientip import client_address
from qbank.core.config import Settings
from qbank.core.db import Database, get_database
from qbank.core.errors import NotFound, TooManyRequests
from qbank.core.ratelimit import LoginRateLimiter
from qbank.core.security import hash_token
from qbank.modules.identity import google_service
from qbank.modules.identity.api import get_settings_from_app, set_auth_cookies
from qbank.modules.identity.google import GoogleClient
from qbank.modules.identity.schemas import (
    AuthMethods,
    GoogleActivationStartRequest,
    GoogleLinkStartRequest,
    GoogleStartRequest,
    GoogleStartResponse,
    LoginMethods,
)

router = APIRouter(prefix="/api/v1", tags=["identity"])

# The cookie that ties a pending Google sign-in to the browser that started it (stops "login CSRF").
FLOW_COOKIE = "qb_google_flow"
FLOW_COOKIE_PATH = "/api/v1/auth/google"
FLOW_MAX_AGE_SECONDS = 600


def _google(request: Request) -> GoogleClient | None:
    google: GoogleClient | None = request.app.state.google
    return google


def _limit(request: Request, what: str) -> None:
    limiter: LoginRateLimiter = request.app.state.login_limiter
    client_ip = client_address(request)
    # The second key is per client too: a shared key would limit everyone's Google sign-in at once.
    wait = limiter.check(client_ip, f"{what}:{client_ip}")
    if wait:
        raise TooManyRequests(
            "Too many attempts. Please wait and try again.", retry_after_seconds=wait
        )


def _set_flow_cookie(
    response: Response, settings: Settings, started: google_service.StartedFlow
) -> None:
    response.set_cookie(
        FLOW_COOKIE,
        started.cookie_value,
        max_age=FLOW_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",  # Google's redirect back is a top-level GET, which Lax allows
        path=FLOW_COOKIE_PATH,
    )


@router.get(
    "/auth/methods",
    summary="Which sign-in methods are on",
    description="For the sign-in page: hides the Google button while Google is not set up.",
)
def auth_methods(request: Request) -> AuthMethods:
    return AuthMethods(password=True, google=_google(request) is not None)


@router.post(
    "/auth/google/start",
    summary="Start signing in with Google",
    description=(
        "Returns the Google address to send the browser to, and sets a short-lived HttpOnly cookie"
        " that only this browser can finish the flow with. Nothing is created: signing in works"
        " only for a Google account somebody already linked."
    ),
    responses={
        404: {"description": "Google sign-in is not set up on this server (`GOOGLE_DISABLED`)"},
        422: {
            "description": "`return_origin` is not an allowed web address"
            " (`RETURN_ORIGIN_NOT_ALLOWED`)"
        },
        429: {"description": "Too many attempts; see the Retry-After header"},
    },
)
def start_google(
    body: GoogleStartRequest,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> GoogleStartResponse:
    google = _google(request)
    if google is None:
        raise NotFound("Google sign-in is not turned on.", code="GOOGLE_DISABLED")
    _limit(request, "google-start")
    started = google_service.start_sign_in(database, settings, google, body.return_origin)
    _set_flow_cookie(response, settings, started)
    return GoogleStartResponse(authorization_url=started.authorization_url)


@router.post(
    "/auth/google/start-activation",
    summary="Start activating an account with Google",
    description=(
        "Like `POST /auth/google/start`, for a person who has an activation link and would rather"
        " use Google than set a password. The link is checked before leaving for Google, and"
        " again when Google calls back; the Google account is then bound to the person the link"
        " was made for. Nothing else is ever created."
    ),
    responses={
        401: {
            "description": "The activation link is unknown, used, replaced, expired, or its"
            " membership or coaching is no longer active (`LINK_INVALID`)"
        },
        404: {"description": "Google sign-in is not set up on this server (`GOOGLE_DISABLED`)"},
        422: {
            "description": "`return_origin` is not an allowed web address"
            " (`RETURN_ORIGIN_NOT_ALLOWED`)"
        },
        429: {"description": "Too many attempts; see the Retry-After header"},
    },
)
def start_google_activation(
    body: GoogleActivationStartRequest,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> GoogleStartResponse:
    google = _google(request)
    if google is None:
        raise NotFound("Google sign-in is not turned on.", code="GOOGLE_DISABLED")
    # Counted per client address and per link, exactly like redeeming the link with a password.
    limiter: LoginRateLimiter = request.app.state.login_limiter
    wait = limiter.check(client_address(request), f"link:{hash_token(body.link_token)}")
    if wait:
        raise TooManyRequests(
            "Too many attempts. Please wait and try again.", retry_after_seconds=wait
        )
    started = google_service.start_activation(
        database, settings, google, body.return_origin, body.link_token
    )
    _set_flow_cookie(response, settings, started)
    return GoogleStartResponse(authorization_url=started.authorization_url)


@router.post(
    "/auth/google/start-link",
    summary="Start linking a Google account to my account",
    description=(
        "For a signed-in person with a password. The current password must be in this very"
        " request: a session alone is never enough. Wrong passwords count towards the sign-in"
        " lockout. Returns the Google address to send the browser to; when Google calls back, the"
        " account is linked (the session stays as it is). Only one Google account can be linked."
    ),
    responses={
        403: {"description": "The password is incorrect (`PASSWORD_INCORRECT`)"},
        404: {"description": "Google sign-in is not set up on this server (`GOOGLE_DISABLED`)"},
        409: {"description": "A Google account is already linked (`ALREADY_LINKED`)"},
        422: {
            "description": "`return_origin` is not an allowed web address"
            " (`RETURN_ORIGIN_NOT_ALLOWED`)"
        },
        429: {"description": "Too many attempts; see the Retry-After header"},
    },
)
def start_google_link(
    body: GoogleLinkStartRequest,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
) -> GoogleStartResponse:
    google = _google(request)
    if google is None:
        raise NotFound("Google sign-in is not turned on.", code="GOOGLE_DISABLED")
    _limit(request, f"google-link:{principal.user_id}")
    started = google_service.start_link(
        database, settings, google, principal, body.return_origin, body.password
    )
    _set_flow_cookie(response, settings, started)
    return GoogleStartResponse(authorization_url=started.authorization_url)


@router.post(
    "/auth/google/unlink",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlink my Google account",
    responses={
        404: {"description": "No Google account is linked (`GOOGLE_NOT_LINKED`)"},
        409: {
            "description": "Google is the only way to sign in; a password must remain"
            " (`NO_OTHER_LOGIN_METHOD`)"
        },
    },
)
def unlink_google(
    principal: CurrentPrincipal,
    request: Request,
    database: Annotated[Database, Depends(get_database)],
) -> None:
    google_service.unlink(database, principal, request.state.request_id)


@router.get(
    "/me/login-methods",
    summary="How I can sign in",
    description="Whether the signed-in account has a password and a linked Google account.",
)
def my_login_methods(
    principal: CurrentPrincipal, database: Annotated[Database, Depends(get_database)]
) -> LoginMethods:
    return google_service.login_methods(database, principal)


@router.get(
    "/auth/google/callback",
    summary="Where Google sends the browser back",
    description=(
        "Not called by our web app. On success the browser is redirected to the home page with a"
        " new session, as after `POST /auth/login`; for linking, to `/profile?google=linked`."
        " Every failure (an unknown or replayed flow, a Google account nobody linked or already"
        " linked, no access any more, Google refusing) is the same redirect, to"
        " `/login?google=failed` (to `/profile?google=failed` when linking, to"
        " `/activate?google=failed` when activating), so nothing is revealed."
    ),
    status_code=status.HTTP_303_SEE_OTHER,
    response_class=RedirectResponse,
    responses={
        303: {
            "description": "Redirect to the home page, to `/profile?google=linked`, or to the"
            " failure address"
        }
    },
)
def google_callback(
    request: Request,
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    google = _google(request)
    # Even if nothing can be processed (Google switched off while the person was away), a failure
    # goes back to the page the person started on.
    finished = google_service.failure_for_state(state)
    if google is not None:
        limiter: LoginRateLimiter = request.app.state.login_limiter
        client_ip = client_address(request)
        # Too many callbacks still end the flow (the flow is used up), but ask nothing of Google.
        throttled = bool(limiter.check(client_ip, f"google-callback:{client_ip}"))
        finished = google_service.finish(
            database,
            settings,
            google,
            cookie=request.cookies.get(FLOW_COOKIE),
            state=state,
            code=code,
            throttled=throttled,
            request_id=request.state.request_id,
        )
    redirect = RedirectResponse(finished.path, status_code=status.HTTP_303_SEE_OTHER)
    if finished.login:
        set_auth_cookies(redirect, settings, finished.login)
    redirect.delete_cookie(FLOW_COOKIE, path=FLOW_COOKIE_PATH)  # one flow, one try
    return redirect
