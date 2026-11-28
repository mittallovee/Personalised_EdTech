"""A model call that is not a run on a question, with the same budget rules (M6 6f, H-05, H-06).

Reading a scanned page is an AI call the ingestion module makes, in a worker, with no principal and
no question. It still has to be metered like every other call: the person's budget is reserved
before the provider is asked (so two jobs cannot both pass it) and settled or given back after.
These three steps are the pieces of ``orchestrator.run_operation`` that do not depend on a
question, exposed for that use:

    reserve_call   a transaction: model and key checked, cost estimated, budget reserved
    make_call      no transaction: the provider is asked
    settle_call    a transaction: the real cost is recorded, or the reservation given back

``run_id`` is any id the caller owns (the ledger needs none to exist as a row); the caller must
settle or release what it reserved, and release what a crashed attempt left behind
(``release_reservation``).
"""

import math
import time
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from qbank.core.errors import Conflict, NotFound, ValidationFailed
from qbank.core.secretbox import Keyring, KeyUnreadable
from qbank.modules.ai import budget
from qbank.modules.ai.catalogue import effective
from qbank.modules.ai.keys import open_key
from qbank.modules.ai.models import AiModel
from qbank.modules.ai.names import Provider
from qbank.modules.ai.orchestrator import ProviderFactory, _cost
from qbank.modules.ai.providers.base import ProviderError, StructuredRequest, StructuredResult
from qbank.modules.ai.settings import usable_model

CHARS_PER_TOKEN = 3  # the orchestrator's own rule of thumb: more tokens than a plain guess
TOKENS_PER_PICTURE = 2500  # what a page picture is assumed to cost as input, when estimating


@dataclass(frozen=True, slots=True)
class MeteredCall:
    """A reservation made, and what is needed to ask the provider."""

    run_id: UUID
    organization_id: UUID
    user_id: UUID
    model: AiModel
    provider: Provider
    api_key: str


@dataclass(frozen=True, slots=True)
class CallOutcome:
    """What the provider did: an answer, or the kind of failure (never any text of either)."""

    result: StructuredResult | None
    failure: str | None  # `TIMEOUT`, `RATE_LIMITED`, ... when there is no result
    latency_ms: int


def estimate_input_tokens(request: StructuredRequest) -> int:
    chars = len(request.system) + len(request.user)
    return math.ceil(chars / CHARS_PER_TOKEN) + TOKENS_PER_PICTURE * len(request.images)


def check_model(
    session: Session, organization_id: UUID, model_id: UUID, *, needs_pictures: bool = False
) -> AiModel:
    """The coaching's model, if a call may use it today: listed, enabled, able to answer in the
    structured form, and (when asked) known to read pictures."""
    model = usable_model(session, organization_id, model_id)
    if needs_pictures and effective(model).supports_vision is not True:
        raise ValidationFailed(
            f"{model.display_name} is not known to read pictures. Choose a model that does (an"
            " admin can record that a model does under Admin, AI, Prices and Economy).",
            code="AI_MODEL_NO_VISION",
        )
    return model


def reserve_call(
    session: Session,
    keyring: Keyring | None,
    *,
    organization_id: UUID,
    user_id: UUID,
    model_id: UUID,
    request: StructuredRequest,
    run_id: UUID,
    needs_pictures: bool = False,
) -> MeteredCall:
    """Check the model and the coaching's key, estimate the cost and reserve it against the person's
    budget (refused with ``AI_BUDGET_EXCEEDED`` when it would pass it)."""
    model = check_model(session, organization_id, model_id, needs_pictures=needs_pictures)
    provider = Provider(model.provider)
    try:
        key = open_key(session, keyring, organization_id, provider)
    except KeyUnreadable:
        raise Conflict(
            "The stored key could not be opened. An admin must enter it again.",
            code="AI_KEY_UNREADABLE",
        ) from None
    if key is None:
        raise Conflict(
            f"No {provider.value.title()} key is stored. An admin adds one under Admin, AI.",
            code="AI_KEY_MISSING",
        )
    estimate: Decimal | None = _cost(
        model, estimate_input_tokens(request), request.max_output_tokens
    )
    budget.reserve(
        session,
        organization_id=organization_id,
        user_id=user_id,
        run_id=run_id,
        estimate_usd=estimate,
    )
    return MeteredCall(run_id, organization_id, user_id, model, provider, key)


def make_call(
    call: MeteredCall, providers: ProviderFactory, request: StructuredRequest
) -> CallOutcome:
    """Ask the provider. No transaction is open and nothing is held while it thinks."""
    began = time.monotonic()
    try:
        result = providers(call.provider).generate_structured(call.api_key, request)
    except ProviderError as problem:
        return CallOutcome(None, problem.kind.value, round((time.monotonic() - began) * 1000))
    return CallOutcome(result, None, round((time.monotonic() - began) * 1000))


def settle_call(session: Session, call: MeteredCall, outcome: CallOutcome) -> Decimal | None:
    """Record what the call cost (from the provider's own figure, else its token counts and the
    model's prices) or, when it failed before being billed, give the reservation back. Returns the
    dollars recorded, or None when nothing was charged or the price is unknown."""
    if outcome.result is None:
        budget.release(session, organization_id=call.organization_id, run_id=call.run_id)
        return None
    result = outcome.result
    actual = result.cost_usd
    if actual is None and result.tokens_in is not None and result.tokens_out is not None:
        actual = _cost(call.model, result.tokens_in, result.tokens_out)
    budget.settle(
        session, organization_id=call.organization_id, run_id=call.run_id, actual_usd=actual
    )
    return actual


def release_reservation(session: Session, *, organization_id: UUID, run_id: UUID) -> None:
    """Give back a reservation an earlier attempt made and never settled (a crash). Safe to call
    when there is none or it is already closed."""
    try:
        budget.release(session, organization_id=organization_id, run_id=run_id)
    except NotFound:  # no reservation was ever made for this id: nothing to give back
        return
