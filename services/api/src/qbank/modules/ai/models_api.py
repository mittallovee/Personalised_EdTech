"""Routes for the coaching's AI model list (M5 design note §4, H-03, H-17)."""

from decimal import Decimal
from time import time
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.errors import Conflict
from qbank.core.etag import IfMatchHeader, etag
from qbank.core.jobs import enqueue
from qbank.core.permissions import Action, require
from qbank.modules.ai import catalogue
from qbank.modules.ai.jobs import REFRESH_MODELS
from qbank.modules.ai.keys import not_configured
from qbank.modules.ai.models import AiModel, ProviderKey
from qbank.modules.ai.names import Provider
from qbank.modules.ai.schemas import (
    ModelOut,
    ModelsOut,
    OverlayOut,
    ProviderStateOut,
    RefreshIn,
    RefreshOut,
    UpdateModel,
)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Only the Owner and admins (`PERMISSION_DENIED`)"}
}


def _text(value: Decimal | None) -> str | None:
    """A price or discount as exact text ("3", "0.1"), never a float."""
    return None if value is None else format(value.normalize(), "f")


def _out(row: AiModel) -> ModelOut:
    facts = catalogue.effective(row)
    return ModelOut(
        id=row.id,
        provider=Provider(row.provider),
        model_id=row.model_id,
        display_name=row.display_name,
        enabled=row.enabled,
        available=row.available,
        supports_vision=facts.supports_vision,
        supports_json=facts.supports_json,
        context_tokens=row.context_tokens,
        price_in_per_mtok=_text(facts.price_in),
        price_out_per_mtok=_text(facts.price_out),
        price_source=facts.price_source,
        batch_supported=facts.batch_supported,
        batch_discount=_text(facts.batch_discount),
        overlay=OverlayOut(
            supports_vision=row.overlay_supports_vision,
            supports_json=row.overlay_supports_json,
            price_in=_text(row.overlay_price_in),
            price_out=_text(row.overlay_price_out),
            batch_supported=row.overlay_batch_supported,
            batch_discount=_text(row.overlay_batch_discount),
        ),
        fetched_at=row.fetched_at,
        revision=row.revision,
    )


@router.get(
    "/models",
    summary="The coaching's AI models, as the providers list them (H-17)",
    description="Owner and admins. Every model the providers' lists have shown for this coaching,"
    " with the facts a run relies on (**effective**: the admin's entry where there is one, else the"
    " provider's, else unknown) and whether it is enabled. `providers` says when each list was last"
    " fetched and how the last try ended. A model the provider no longer lists stays here as"
    " `available: false`.",
    responses=_DENIED,
)
def list_models(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    provider: Provider | None = None,
    enabled: bool | None = None,
    available: bool | None = None,
) -> ModelsOut:
    with database.transaction(principal.tenant_context) as session:
        rows, states = catalogue.list_models(
            session, principal, provider=provider, enabled=enabled, available=available
        )
        return ModelsOut(
            data=[_out(row) for row in rows],
            providers=[
                ProviderStateOut(
                    provider=state.provider,
                    configured=state.configured,
                    last_refreshed_at=state.last_refreshed_at,
                    last_error=state.last_error,
                )
                for state in states
            ],
        )


@router.post(
    "/models/refresh",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Fetch a provider's model list again (H-17)",
    description="Owner and admins. Starts a background job that asks the provider for its list"
    " with the coaching's stored key and updates the rows. Pressing it twice in a minute starts"
    " one job. Read `providers` in the model list to see when it finished and whether it worked;"
    " a failure is not retried by itself.",
    responses={
        **_DENIED,
        409: {
            "description": "No key is stored for that provider (`AI_KEY_MISSING`), or the server"
            " has no master encryption key (`AI_NOT_CONFIGURED`)"
        },
    },
)
def refresh_models(
    body: RefreshIn,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> RefreshOut:
    require(principal, Action.MANAGE_AI_SETTINGS)
    if request.app.state.ai_keyring is None:
        raise not_configured()
    with database.transaction(principal.tenant_context) as session:
        stored = session.scalars(
            select(ProviderKey.id).where(
                ProviderKey.organization_id == principal.tenant_context.organization_id,
                ProviderKey.provider == body.provider.value,
            )
        ).first()
        if stored is None:
            raise Conflict(
                "Store this provider's key first.",
                code="AI_KEY_MISSING",
            )
        job_id = enqueue(
            session,
            REFRESH_MODELS,
            {"provider": body.provider.value},
            context=principal.tenant_context,
            idempotency_key=f"refresh-{body.provider.value}-{int(time() // 60)}",
            request_id=request.state.request_id,
            max_attempts=1,
        )
    return RefreshOut(job_id=job_id)


@router.patch(
    "/models/{model_id}",
    summary="Enable or disable a model, or set the admin's own facts about it (H-03, H-17)",
    description="Owner and admins. `enabled` offers the model to faculty (a model the provider no"
    " longer lists cannot be enabled: `AI_MODEL_UNAVAILABLE`). `overlay` holds the admin's own"
    " capability and price entries, which win over the provider's; send only what changes, and"
    " `null` to remove one. Send the ETag you last read in `If-Match`. Written to the audit log.",
    responses={
        **_DENIED,
        404: {"description": "No such model (`NOT_FOUND`)"},
        409: {"description": "The provider no longer lists it (`AI_MODEL_UNAVAILABLE`)"},
        412: {"description": "Changed since you read it (`REVISION_STALE`)"},
        428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
    },
)
def update_model(
    model_id: UUID,
    body: UpdateModel,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> ModelOut:
    overlay = None
    if body.overlay is not None:
        overlay = catalogue.OverlayPatch(
            {
                f"overlay_{name}": getattr(body.overlay, name)
                for name in body.overlay.model_fields_set
            }
        )
    with database.transaction(principal.tenant_context) as session:
        row = catalogue.update_model(
            session,
            principal,
            model_id,
            if_match=if_match,
            enabled=body.enabled,
            overlay=overlay,
            request_id=request.state.request_id,
        )
        result = _out(row)
    response.headers["ETag"] = etag(result.revision)
    return result
