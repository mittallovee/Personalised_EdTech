"""What a person may pick in the "run AI" dialog (M5 design note §11; H-03, H-17).

The admin pages list every model and every setting, and are for admins. Faculty need only the
short list a run would accept: models that are enabled, still listed by the provider, able to
return structured answers and with a key stored, plus the model and mode offered first for each
operation. Nothing here exposes a key, a fallback or an admin's overlay.
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import PreconditionFailed
from qbank.core.permissions import Action, require
from qbank.modules.ai.catalogue import effective
from qbank.modules.ai.models import AiModel, OperationSetting, ProviderKey
from qbank.modules.ai.names import Mode, Operation, Provider
from qbank.modules.ai.providers.base import AIProvider, BatchProvider


@dataclass(frozen=True, slots=True)
class ModelChoice:
    model: AiModel
    price_in: Decimal | None
    price_out: Decimal | None
    economy: bool  # whether an Economy (batch) run is possible with this model


@dataclass(frozen=True, slots=True)
class OperationChoice:
    operation: Operation
    default_model_id: UUID | None  # None when unset or no longer usable
    mode: Mode


@dataclass(frozen=True, slots=True)
class Options:
    operations: list[OperationChoice]
    models: list[ModelChoice]


def read_options(
    session: Session, principal: Principal, providers: Callable[[Provider], AIProvider]
) -> Options:
    require(principal, Action.USE_AI)
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:
        raise PreconditionFailed("Choose a coaching to use AI in.")
    keyed = set(
        session.scalars(
            select(ProviderKey.provider).where(ProviderKey.organization_id == organization_id)
        )
    )
    choices: list[ModelChoice] = []
    for model in session.scalars(
        select(AiModel)
        .where(
            AiModel.organization_id == organization_id,
            AiModel.enabled.is_(True),
            AiModel.available.is_(True),
        )
        .order_by(AiModel.provider, AiModel.display_name)
    ):
        facts = effective(model)
        if facts.supports_json is False or model.provider not in keyed:
            continue
        priced = facts.price_in is not None and facts.price_out is not None
        batch = facts.batch_supported and isinstance(
            providers(Provider(model.provider)), BatchProvider
        )
        choices.append(ModelChoice(model, facts.price_in, facts.price_out, batch and priced))
    usable = {choice.model.id for choice in choices}
    settings = {
        row.operation: row
        for row in session.scalars(
            select(OperationSetting).where(OperationSetting.organization_id == organization_id)
        )
    }
    operations = []
    for operation in Operation:
        row = settings.get(operation.value)
        first = row.default_model_id if row is not None else None
        operations.append(
            OperationChoice(
                operation,
                first if first in usable else None,
                Mode(row.default_mode) if row is not None else Mode.NOW,
            )
        )
    return Options(operations, choices)
