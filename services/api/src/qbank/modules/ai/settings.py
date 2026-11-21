"""What an admin sets for the AI features (M5 design note §4, §7; H-03, H-05, H-06).

Three small things, each saved under ``If-Match`` so two admins cannot overwrite each other unseen
(an unsaved thing reads as revision 0):

- the **rate** (rupees per US dollar, entered by the admin because providers bill in dollars and
  budgets are in rupees) and the **default monthly budget** per person;
- per operation, the model offered first, **Now** or **Economy**, and up to two fallback models;
- a person's **own budget**, where it differs from the default.

A default must name a model that is listed, enabled and able to return JSON; Economy only a model
the admin has marked as offering batch runs. Later the admin may disable a model that is still a
default: that is allowed and shown as a ``problem`` on the operation, and a run refuses it.
"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import Conflict, NotFound, PreconditionFailed, ValidationFailed
from qbank.core.etag import etag, require_if_match
from qbank.core.permissions import Action, require
from qbank.modules.ai import catalogue
from qbank.modules.ai.models import AiBudget, AiModel, AiSettings, OperationSetting
from qbank.modules.ai.names import Mode, Operation
from qbank.modules.audit.public import record_event
from qbank.modules.organizations.public import find_active_membership

SETTINGS_ENTITY = "ai_settings"
OPERATION_ENTITY = "ai_operation"
BUDGET_ENTITY = "ai_budget"
MOST_FALLBACKS = 2


@dataclass(frozen=True, slots=True)
class SettingsView:
    revision: int  # 0 until first saved
    usd_to_inr: Decimal | None
    default_budget_inr: Decimal | None


@dataclass(frozen=True, slots=True)
class OperationView:
    operation: Operation
    revision: int  # 0 until first saved
    default_model: AiModel | None
    mode: Mode
    fallbacks: list[AiModel]
    problem: str | None  # why a run would refuse this setting today, else None


@dataclass(frozen=True, slots=True)
class BudgetView:
    user_id: UUID
    monthly_inr: Decimal
    revision: int


def _org(principal: Principal) -> UUID:
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:  # the permission check already refuses this
        raise PreconditionFailed("No coaching to change AI settings for.")
    return organization_id


def _text(value: Decimal | None) -> str | None:
    return None if value is None else format(value.normalize(), "f")


# --- Rate and default budget ---------------------------------------------------------------------


def _settings_view(row: AiSettings | None) -> SettingsView:
    if row is None:
        return SettingsView(0, None, None)
    return SettingsView(row.revision, row.usd_to_inr, row.default_budget_inr)


def get_settings(session: Session, principal: Principal) -> SettingsView:
    require(principal, Action.MANAGE_AI_SETTINGS)
    return _settings_view(session.scalars(select(AiSettings)).first())


def save_settings(
    session: Session,
    principal: Principal,
    *,
    usd_to_inr: Decimal | None,
    default_budget_inr: Decimal | None,
    if_match: str | None,
    request_id: str | None,
) -> SettingsView:
    """Replace the rate and the default budget (``None`` = not set)."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = _org(principal)
    row = session.scalars(
        select(AiSettings).where(AiSettings.organization_id == organization_id).with_for_update()
    ).first()
    require_if_match(if_match, row.revision if row is not None else 0)
    before = _settings_view(row)
    if row is None:
        row = AiSettings(
            organization_id=organization_id,
            usd_to_inr=usd_to_inr,
            default_budget_inr=default_budget_inr,
            revision=1,
            updated_by=principal.user_id,
        )
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:  # another admin saved the first version at the same moment
            raise PreconditionFailed(
                "Someone else changed this in the meantime. Reload it and try again.",
                details={"current_etag": etag(1)},
            ) from None
    else:
        row.usd_to_inr = usd_to_inr
        row.default_budget_inr = default_budget_inr
        row.revision += 1
        row.updated_by = principal.user_id
        session.flush()
    after = _settings_view(row)
    record_event(
        session,
        action="AI_SETTINGS_CHANGED",
        entity_type=SETTINGS_ENTITY,
        entity_id=organization_id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before={
            "usd_to_inr": _text(before.usd_to_inr),
            "default_budget_inr": _text(before.default_budget_inr),
        },
        after={
            "usd_to_inr": _text(after.usd_to_inr),
            "default_budget_inr": _text(after.default_budget_inr),
        },
    )
    return after


# --- Operation defaults --------------------------------------------------------------------------


def _problem(model: AiModel | None) -> str | None:
    if model is None:
        return None
    if not model.available:
        return "MODEL_UNAVAILABLE"
    if not model.enabled:
        return "MODEL_DISABLED"
    return None


def _operation_view(
    operation: Operation, row: OperationSetting | None, models: dict[UUID, AiModel]
) -> OperationView:
    if row is None:
        return OperationView(operation, 0, None, Mode.NOW, [], None)
    default = models.get(row.default_model_id) if row.default_model_id else None
    fallbacks = [
        models[model_id]
        for model_id in (row.fallback_1_id, row.fallback_2_id)
        if model_id is not None and model_id in models
    ]
    return OperationView(
        operation, row.revision, default, Mode(row.default_mode), fallbacks, _problem(default)
    )


def list_operations(session: Session, principal: Principal) -> list[OperationView]:
    """All four operations, in a fixed order, with what is set (or the built-in start)."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = _org(principal)
    rows = {
        row.operation: row
        for row in session.scalars(
            select(OperationSetting).where(OperationSetting.organization_id == organization_id)
        )
    }
    wanted = {
        model_id
        for row in rows.values()
        for model_id in (row.default_model_id, row.fallback_1_id, row.fallback_2_id)
        if model_id is not None
    }
    models = {
        model.id: model
        for model in session.scalars(
            select(AiModel).where(
                AiModel.organization_id == organization_id, AiModel.id.in_(wanted)
            )
        )
    }
    return [
        _operation_view(operation, rows.get(operation.value), models) for operation in Operation
    ]


def _usable_model(session: Session, organization_id: UUID, model_id: UUID) -> AiModel:
    model = session.scalars(
        select(AiModel).where(AiModel.id == model_id, AiModel.organization_id == organization_id)
    ).first()
    if model is None:
        raise ValidationFailed(
            "There is no such model here.",
            code="AI_MODEL_NOT_FOUND",
            details={"model": str(model_id)},
        )
    if not model.available:
        raise Conflict(
            f"The provider no longer lists {model.display_name}.", code="AI_MODEL_UNAVAILABLE"
        )
    if not model.enabled:
        raise Conflict(
            f"{model.display_name} is not enabled. Enable it under the models first.",
            code="AI_MODEL_NOT_ENABLED",
        )
    if catalogue.effective(model).supports_json is False:
        raise Conflict(
            f"{model.display_name} cannot return the structured answers these operations need.",
            code="AI_MODEL_NO_JSON",
        )
    return model


def save_operation(
    session: Session,
    principal: Principal,
    operation: Operation,
    *,
    default_model_id: UUID | None,
    mode: Mode,
    fallback_model_ids: list[UUID],
    if_match: str | None,
    request_id: str | None,
) -> OperationView:
    """Replace the setting of one operation."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = _org(principal)
    chain = ([default_model_id] if default_model_id is not None else []) + fallback_model_ids
    if len(fallback_model_ids) > MOST_FALLBACKS:
        raise ValidationFailed(
            f"At most {MOST_FALLBACKS} fallback models.", code="AI_FALLBACKS_TOO_MANY"
        )
    if fallback_model_ids and default_model_id is None:
        raise ValidationFailed(
            "Choose the first model before the fallbacks.", code="AI_FALLBACK_WITHOUT_DEFAULT"
        )
    if len(set(chain)) != len(chain):
        raise ValidationFailed(
            "A model can appear only once in the chain.", code="AI_MODEL_REPEATED"
        )
    if default_model_id is None and mode is Mode.ECONOMY:
        raise ValidationFailed(
            "Choose a model before choosing Economy.", code="AI_ECONOMY_NEEDS_MODEL"
        )
    models = {model_id: _usable_model(session, organization_id, model_id) for model_id in chain}
    if mode is Mode.ECONOMY and default_model_id is not None:
        first = models[default_model_id]
        if not catalogue.effective(first).batch_supported:
            raise Conflict(
                f"{first.display_name} is not marked as offering Economy runs. Mark it on the"
                " model first (and enter its Economy price if the provider does not publish it).",
                code="AI_ECONOMY_UNAVAILABLE",
            )

    row = session.scalars(
        select(OperationSetting)
        .where(
            OperationSetting.organization_id == organization_id,
            OperationSetting.operation == operation.value,
        )
        .with_for_update()
    ).first()
    require_if_match(if_match, row.revision if row is not None else 0)
    before = _operation_facts(row, models=None)
    fallback_1 = fallback_model_ids[0] if len(fallback_model_ids) > 0 else None
    fallback_2 = fallback_model_ids[1] if len(fallback_model_ids) > 1 else None
    if row is None:
        row = OperationSetting(
            organization_id=organization_id,
            operation=operation.value,
            default_model_id=default_model_id,
            default_mode=mode.value,
            fallback_1_id=fallback_1,
            fallback_2_id=fallback_2,
            revision=1,
            updated_by=principal.user_id,
        )
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:
            raise PreconditionFailed(
                "Someone else changed this in the meantime. Reload it and try again.",
                details={"current_etag": etag(1)},
            ) from None
    else:
        row.default_model_id = default_model_id
        row.default_mode = mode.value
        row.fallback_1_id = fallback_1
        row.fallback_2_id = fallback_2
        row.revision += 1
        row.updated_by = principal.user_id
        session.flush()
    record_event(
        session,
        action="AI_OPERATION_DEFAULT_CHANGED",
        entity_type=OPERATION_ENTITY,
        entity_id=row.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before=before,
        after=_operation_facts(row, models=models),
    )
    return _operation_view(operation, row, models)


def _operation_facts(
    row: OperationSetting | None, *, models: dict[UUID, AiModel] | None
) -> dict[str, object]:
    """The setting as the audit log keeps it: model ids, and the names where they are known."""
    if row is None:
        return {"operation": None, "default_model_id": None, "mode": None, "fallback_model_ids": []}

    def name(model_id: UUID | None) -> str | None:
        if model_id is None or models is None or model_id not in models:
            return None
        return f"{models[model_id].provider}/{models[model_id].model_id}"

    ids = [row.fallback_1_id, row.fallback_2_id]
    return {
        "operation": row.operation,
        "default_model_id": str(row.default_model_id) if row.default_model_id else None,
        "default_model": name(row.default_model_id),
        "mode": row.default_mode,
        "fallback_model_ids": [str(model_id) for model_id in ids if model_id is not None],
    }


# --- Budgets of single people ---------------------------------------------------------------------


def list_budgets(session: Session, principal: Principal) -> list[BudgetView]:
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = _org(principal)
    rows = session.scalars(
        select(AiBudget)
        .where(AiBudget.organization_id == organization_id)
        .order_by(AiBudget.updated_at, AiBudget.id)
    )
    return [BudgetView(row.user_id, row.monthly_inr, row.revision) for row in rows]


def _member_of_this_coaching(session: Session, organization_id: UUID, user_id: UUID) -> None:
    membership = find_active_membership(session, user_id)
    if membership is None or membership.organization_id != organization_id:
        raise NotFound("There is no such member here.")


def set_budget(
    session: Session,
    principal: Principal,
    user_id: UUID,
    *,
    monthly_inr: Decimal,
    if_match: str | None,
    request_id: str | None,
) -> BudgetView:
    """Give one member a monthly budget of their own (``0`` = no AI use)."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = _org(principal)
    _member_of_this_coaching(session, organization_id, user_id)
    row = session.scalars(
        select(AiBudget)
        .where(AiBudget.organization_id == organization_id, AiBudget.user_id == user_id)
        .with_for_update()
    ).first()
    require_if_match(if_match, row.revision if row is not None else 0)
    before = _text(row.monthly_inr) if row is not None else None
    if row is None:
        row = AiBudget(
            organization_id=organization_id,
            user_id=user_id,
            monthly_inr=monthly_inr,
            revision=1,
            updated_by=principal.user_id,
        )
        try:
            with session.begin_nested():
                session.add(row)
                session.flush()
        except IntegrityError:
            raise PreconditionFailed(
                "Someone else changed this in the meantime. Reload it and try again.",
                details={"current_etag": etag(1)},
            ) from None
    else:
        row.monthly_inr = monthly_inr
        row.revision += 1
        row.updated_by = principal.user_id
        session.flush()
    record_event(
        session,
        action="AI_BUDGET_CHANGED",
        entity_type=BUDGET_ENTITY,
        entity_id=row.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before={"user_id": str(user_id), "monthly_inr": before},
        after={"user_id": str(user_id), "monthly_inr": _text(row.monthly_inr)},
    )
    return BudgetView(user_id, row.monthly_inr, row.revision)


def clear_budget(
    session: Session,
    principal: Principal,
    user_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
) -> None:
    """Take a member's own budget away, so the coaching's default applies to them again."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    organization_id = _org(principal)
    row = session.scalars(
        select(AiBudget)
        .where(AiBudget.organization_id == organization_id, AiBudget.user_id == user_id)
        .with_for_update()
    ).first()
    if row is None:
        raise NotFound("This member has no budget of their own.")
    require_if_match(if_match, row.revision)
    before = _text(row.monthly_inr)
    entity_id = row.id
    session.delete(row)
    session.flush()
    record_event(
        session,
        action="AI_BUDGET_CLEARED",
        entity_type=BUDGET_ENTITY,
        entity_id=entity_id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before={"user_id": str(user_id), "monthly_inr": before},
        after={"user_id": str(user_id), "monthly_inr": None},
    )
