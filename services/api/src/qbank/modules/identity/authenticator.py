"""Session-cookie authentication for the web app (API style guide §7)."""

from fastapi import Request

from qbank.core.auth import CSRF_HEADER, SESSION_COOKIE, Principal
from qbank.core.config import Settings
from qbank.core.db import Database
from qbank.core.errors import PermissionDenied
from qbank.core.security import token_matches
from qbank.modules.identity.service import resolve_session

CSRF_COOKIE = "qb_csrf"
# Requests that change something must prove they come from our web app (CSRF protection).
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class SessionCookieAuthenticator:
    def __init__(self, database: Database, settings: Settings) -> None:
        self._database = database
        self._settings = settings

    def authenticate(self, request: Request) -> Principal | None:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            return None
        checked = resolve_session(self._database, self._settings, token)
        if checked is None:
            return None
        if request.method not in _SAFE_METHODS:
            csrf = request.headers.get(CSRF_HEADER, "")
            if not csrf or not token_matches(csrf, checked.csrf_token_hash):
                raise PermissionDenied(
                    "This request is missing a valid CSRF token.", code="CSRF_TOKEN_INVALID"
                )
        return checked.principal
