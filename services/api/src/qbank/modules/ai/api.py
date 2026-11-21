"""Routes for a coaching's AI provider keys (M5 design note §4, H-02, ADR-0023)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.secretbox import Keyring
from qbank.modules.ai import keys as service
from qbank.modules.ai.names import Provider
from qbank.modules.ai.schemas import KeysOut, ProviderKeyOut, SetKey

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Only the Owner and admins (`PERMISSION_DENIED`)"}
}


def _keyring(request: Request) -> Keyring | None:
    keyring: Keyring | None = request.app.state.ai_keyring
    return keyring


def _out(item: service.KeyStatus) -> ProviderKeyOut:
    return ProviderKeyOut(
        provider=item.provider,
        configured=item.configured,
        last4=item.last4,
        updated_at=item.updated_at,
    )


@router.get(
    "/keys",
    summary="Which provider keys the coaching has stored (H-02)",
    description="Owner and admins. One entry per provider: whether a key is stored and its last"
    " four characters. **A key is never returned.** `encryption_ready` is false when the server"
    " has no master encryption key, and then no key can be stored.",
    responses=_DENIED,
)
def list_keys(
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> KeysOut:
    with database.transaction(principal.tenant_context) as session:
        found = service.list_keys(session, principal)
    return KeysOut(
        encryption_ready=_keyring(request) is not None, data=[_out(item) for item in found]
    )


@router.put(
    "/keys/{provider}",
    summary="Store or replace the coaching's key for a provider (H-02)",
    description="Owner and admins. The key is sealed on the server with the master encryption key"
    " and cannot be read back: write-only. Replacing a key replaces it for every run from now on."
    " The change is written to the audit log with the last four characters only.",
    responses={
        **_DENIED,
        409: {"description": "The server has no master encryption key (`AI_NOT_CONFIGURED`)"},
        422: {"description": "Does not look like an API key (`AI_KEY_INVALID`)"},
    },
)
def set_key(
    provider: Provider,
    body: SetKey,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> ProviderKeyOut:
    with database.transaction(principal.tenant_context) as session:
        stored = service.set_key(
            session,
            principal,
            _keyring(request),
            provider,
            body.key.get_secret_value(),
            request_id=request.state.request_id,
        )
        return _out(stored)


@router.delete(
    "/keys/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove the coaching's key for a provider",
    description="Owner and admins. AI runs that need this provider stop working until a key is"
    " stored again. Written to the audit log.",
    responses={**_DENIED, 404: {"description": "No key is stored for that provider (`NOT_FOUND`)"}},
)
def delete_key(
    provider: Provider,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> Response:
    with database.transaction(principal.tenant_context) as session:
        service.delete_key(session, principal, provider, request_id=request.state.request_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
