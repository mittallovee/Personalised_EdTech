"""The coaching's list of AI models: refreshed from the providers, enabled by an admin (H-03, H-17).

A refresh copies what each provider's own list says (name, capabilities, context size, prices) into
``ai_models``; it never changes what an admin set (the overlay, ``enabled``). A model that is no
longer listed stays on record as unavailable, so a run that used it can still be explained, and it
cannot be chosen. The facts a run needs (can it return JSON, what does it cost) are the
**effective** ones: the admin's overlay where set, else the provider's, else unknown.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, PreconditionFailed
from qbank.core.etag import require_if_match
from qbank.core.permissions import Action, require
from qbank.modules.ai.models import AiModel, ProviderKey
from qbank.modules.ai.names import Provider
from qbank.modules.ai.providers.base import ModelInfo
from qbank.modules.audit.public import record_event

ENTITY_TYPE = "ai_model"
MOST_MODELS = 2000  # of one provider; a longer list is cut, so a mistake cannot fill the table
_CENT = Decimal("0.000001")
_LARGEST_PRICE = Decimal("100000000")  # dollars per million tokens: far beyond any real price

PriceSource = Literal["PROVIDER", "ADMIN", "UNKNOWN"]


@dataclass(frozen=True, slots=True)
class Effective:
    """What a run may rely on: the overlay where the admin set one, else what the provider said."""

    supports_vision: bool | None
    supports_json: bool | None
    price_in: Decimal | None
    price_out: Decimal | None
    price_source: PriceSource
    batch_supported: bool
    batch_discount: Decimal | None


def effective(model: AiModel) -> Effective:
    overlaid = model.overlay_price_in is not None or model.overlay_price_out is not None
    price_in = model.overlay_price_in if model.overlay_price_in is not None else model.price_in
    price_out = model.overlay_price_out if model.overlay_price_out is not None else model.price_out
    source: PriceSource = (
        "ADMIN"
        if overlaid
        else "PROVIDER"
        if (price_in is not None or price_out is not None)
        else "UNKNOWN"
    )
    return Effective(
        supports_vision=(
            model.overlay_supports_vision
            if model.overlay_supports_vision is not None
            else model.supports_vision
        ),
        supports_json=(
            model.overlay_supports_json
            if model.overlay_supports_json is not None
            else model.supports_json
        ),
        price_in=price_in,
        price_out=price_out,
        price_source=source,
        batch_supported=model.overlay_batch_supported is True,
        batch_discount=model.overlay_batch_discount,
    )


def _price(value: Decimal | None) -> Decimal | None:
    """A price as the column keeps it (six decimals), or unknown when outside any real range."""
    if value is None or not value.is_finite() or value < 0 or value >= _LARGEST_PRICE:
        return None
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class Applied:
    added: int
    updated: int
    gone: int


def apply_listing(
    session: Session,
    organization_id: UUID,
    provider: Provider,
    listed: list[ModelInfo],
    *,
    now: datetime | None = None,
) -> Applied:
    """Bring the provider's rows up to date with a fresh list. New models start disabled; models
    that are gone become unavailable; the overlay and ``enabled`` are never touched."""
    moment = now or datetime.now(UTC)
    existing = {
        row.model_id: row
        for row in session.scalars(
            select(AiModel).where(
                AiModel.organization_id == organization_id, AiModel.provider == provider.value
            )
        )
    }
    seen: set[str] = set()
    added = updated = 0
    for info in listed[:MOST_MODELS]:
        if info.model_id in seen or not 1 <= len(info.model_id) <= 200:
            continue
        seen.add(info.model_id)
        facts = {
            "display_name": (info.display_name or info.model_id)[:300],
            "supports_vision": info.supports_vision,
            "supports_json": info.supports_json,
            "context_tokens": info.context_tokens,
            "price_in": _price(info.price_in_per_mtok),
            "price_out": _price(info.price_out_per_mtok),
        }
        row = existing.get(info.model_id)
        if row is None:
            session.add(
                AiModel(
                    organization_id=organization_id,
                    provider=provider.value,
                    model_id=info.model_id,
                    fetched_at=moment,
                    **facts,
                )
            )
            added += 1
            continue
        changed = not row.available or any(
            getattr(row, name) != value for name, value in facts.items()
        )
        for name, value in facts.items():
            setattr(row, name, value)
        row.available = True
        row.fetched_at = moment
        if changed:
            row.updated_at = moment
            row.revision += 1
            updated += 1
    gone = 0
    for model_id, row in existing.items():
        if model_id not in seen and row.available:
            row.available = False
            row.fetched_at = moment
            row.updated_at = moment
            row.revision += 1
            gone += 1
    session.flush()
    return Applied(added, updated, gone)


def record_refresh(
    session: Session, organization_id: UUID, provider: Provider, *, error: str | None
) -> None:
    """Note on the provider's key when its list was last fetched and how the last try ended."""
    row = session.scalars(
        select(ProviderKey).where(
            ProviderKey.organization_id == organization_id, ProviderKey.provider == provider.value
        )
    ).first()
    if row is None:
        return
    row.models_error = error
    if error is None:
        row.models_fetched_at = datetime.now(UTC)
    session.flush()


@dataclass(frozen=True, slots=True)
class ProviderState:
    provider: Provider
    configured: bool
    last_refreshed_at: datetime | None
    last_error: str | None


def provider_states(session: Session, organization_id: UUID) -> list[ProviderState]:
    rows = {
        row.provider: row
        for row in session.scalars(
            select(ProviderKey).where(ProviderKey.organization_id == organization_id)
        )
    }
    return [
        ProviderState(
            provider,
            provider.value in rows,
            rows[provider.value].models_fetched_at if provider.value in rows else None,
            rows[provider.value].models_error if provider.value in rows else None,
        )
        for provider in Provider
    ]


def list_models(
    session: Session,
    principal: Principal,
    *,
    provider: Provider | None = None,
    enabled: bool | None = None,
    available: bool | None = None,
) -> tuple[list[AiModel], list[ProviderState]]:
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise PreconditionFailed("No coaching to list models for.")
    query = select(AiModel).where(AiModel.organization_id == organization_id)
    if provider is not None:
        query = query.where(AiModel.provider == provider.value)
    if enabled is not None:
        query = query.where(AiModel.enabled.is_(enabled))
    if available is not None:
        query = query.where(AiModel.available.is_(available))
    rows = list(session.scalars(query.order_by(AiModel.provider, AiModel.model_id)))
    return rows, provider_states(session, organization_id)


@dataclass(frozen=True, slots=True)
class OverlayPatch:
    """Only the fields that were sent: ``None`` as a value clears the overlay of that fact."""

    values: dict[str, object]


_OVERLAY_FIELDS = (
    "overlay_supports_vision",
    "overlay_supports_json",
    "overlay_price_in",
    "overlay_price_out",
    "overlay_batch_supported",
    "overlay_batch_discount",
)


def _facts(model: AiModel) -> dict[str, object]:
    return {
        name: (
            str(getattr(model, name))
            if isinstance(getattr(model, name), Decimal)
            else getattr(model, name)
        )
        for name in ("enabled", *_OVERLAY_FIELDS)
    }


def update_model(
    session: Session,
    principal: Principal,
    model_id: UUID,
    *,
    if_match: str | None,
    enabled: bool | None,
    overlay: OverlayPatch | None,
    request_id: str | None,
) -> AiModel:
    """Enable or disable a model and/or set the admin overlay. Audited with before and after."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise PreconditionFailed("No coaching to change models for.")
    row = session.scalars(
        select(AiModel)
        .where(AiModel.id == model_id, AiModel.organization_id == organization_id)
        .with_for_update()
    ).first()
    if row is None:
        raise NotFound("No such model.")
    require_if_match(if_match, row.revision)
    before = _facts(row)
    if enabled is not None and enabled != row.enabled:
        if enabled and not row.available:
            raise Conflict(
                "The provider no longer lists this model, so it cannot be enabled.",
                code="AI_MODEL_UNAVAILABLE",
            )
        row.enabled = enabled
    if overlay is not None:
        for name, value in overlay.values.items():
            if name not in _OVERLAY_FIELDS:
                continue
            setattr(row, name, value)
    after = _facts(row)
    if after != before:
        row.revision += 1
        row.updated_at = datetime.now(UTC)
        session.flush()
        action = (
            ("AI_MODEL_ENABLED" if row.enabled else "AI_MODEL_DISABLED")
            if before["enabled"] != after["enabled"]
            else "AI_MODEL_OVERLAY_CHANGED"
        )
        record_event(
            session,
            action=action,
            entity_type=ENTITY_TYPE,
            entity_id=row.id,
            organization_id=organization_id,
            actor_user_id=principal.user_id,
            actor_is_platform=principal.acting_organization_id is not None,
            request_id=request_id,
            before={"provider": row.provider, "model": row.model_id, **before},
            after={"provider": row.provider, "model": row.model_id, **after},
        )
    return row
