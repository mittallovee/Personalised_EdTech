from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse

from qbank.core.clientip import client_address
from qbank.core.config import Settings
from qbank.core.db import Database, get_database
from qbank.core.errors import NotFound, TooManyRequests
from qbank.core.ratelimit import LoginRateLimiter
from qbank.modules.identity import google_service
from qbank.modules.identity.api import get_settings_from_app, set_auth_cookies
from qbank.modules.identity.google import GoogleClient
from qbank.modules.identity.schemas import AuthMethods, GoogleStartRequest, GoogleStartResponse

router = APIRouter(prefix="/api/v1", tags=["identity"])

# The cookie that ties a pending Google sign-in to the browser that started it (stops "login CSRF").
FLOW_COOKIE = "qb_google_flow"
FLOW_COOKIE_PATH = "/api/v1/auth/google"
FLOW_MAX_AGE_SECONDS = 600
# Where the browser lands after Google calls back. Relative, so it stays on the web address the
# person is already using (the web app proxies /api, ADR-0014).
SIGNED_IN_PATH = "/"
FAILED_PATH = "/login?google=failed"


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
    response.set_cookie(
        FLOW_COOKIE,
        started.cookie_value,
        max_age=FLOW_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",  # Google's redirect back is a top-level GET, which Lax allows
        path=FLOW_COOKIE_PATH,
    )
    return GoogleStartResponse(authorization_url=started.authorization_url)


@router.get(
    "/auth/google/callback",
    summary="Where Google sends the browser back",
    description=(
        "Not called by our web app. On success the browser is redirected to the home page with a"
        " new session, as after `POST /auth/login`. Every failure (an unknown or replayed flow, a"
        " Google account nobody linked, no access any more, Google refusing) is the same"
        " redirect to `/login?google=failed`, so nothing is revealed."
    ),
    status_code=status.HTTP_303_SEE_OTHER,
    response_class=RedirectResponse,
    responses={303: {"description": "Redirect to the home page, or to `/login?google=failed`"}},
)
def google_callback(
    request: Request,
    database: Annotated[Database, Depends(get_database)],
    settings: Annotated[Settings, Depends(get_settings_from_app)],
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    google = _google(request)
    result = None
    if google is not None:
        limiter: LoginRateLimiter = request.app.state.login_limiter
        client_ip = client_address(request)
        if not limiter.check(client_ip, f"google-callback:{client_ip}"):
            result = google_service.finish(
                database,
                settings,
                google,
                cookie=request.cookies.get(FLOW_COOKIE),
                state=state,
                code=code,
                request_id=request.state.request_id,
            )
    redirect = RedirectResponse(
        SIGNED_IN_PATH if result else FAILED_PATH, status_code=status.HTTP_303_SEE_OTHER
    )
    if result:
        set_auth_cookies(redirect, settings, result)
    redirect.delete_cookie(FLOW_COOKIE, path=FLOW_COOKIE_PATH)  # one flow, one try
    return redirect
