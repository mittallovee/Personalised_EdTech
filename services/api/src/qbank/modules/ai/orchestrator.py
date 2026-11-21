"""The one path every AI run takes (M5 design note §6; H-04, H-05, H-06).

    A  permission, inputs, prompt, model, estimate, budget reserved, run recorded  (a transaction)
    B  the provider call, and a fallback to the next model when it fails           (none open)
    C  validate, record attempts, settle or release the budget, apply              (a transaction)

The provider call is never made inside a transaction: nothing is held (no locks, no connection in
use) while a slow provider answers. The budget is reserved in A and settled or released in C, so two
runs cannot both pass the same budget, and a run that never reaches C (a crash) is found and closed
by ``abandon_stale`` the next time the same person starts a run.
"""

import hashlib
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_UP, Decimal
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.db import Database
from qbank.core.errors import Conflict, NotFound, ValidationFailed
from qbank.core.permissions import Action, is_allowed, require
from qbank.core.secretbox import Keyring, KeyUnreadable
from qbank.modules.ai import budget, locked, prompts
from qbank.modules.ai.catalogue import effective
from qbank.modules.ai.keys import open_key
from qbank.modules.ai.models import AiModel, AiRun, AiRunAttempt, OperationSetting
from qbank.modules.ai.names import Mode, Operation, Provider
from qbank.modules.ai.operations import solve, tag, verify
from qbank.modules.ai.operations.base import ApplyStep, BadOutput, Prepared, RunBase
from qbank.modules.ai.providers.base import (
    AIProvider,
    ProviderError,
    StructuredRequest,
    StructuredResult,
)
from qbank.modules.ai.settings import usable_model
from qbank.modules.audit.public import record_event
from qbank.modules.questions.public import QuestionForAi, read_for_ai

log = structlog.get_logger("qbank.ai")

ProviderFactory = Callable[[Provider], AIProvider]

STALE_AFTER = timedelta(minutes=15)  # three provider attempts of two minutes, with room to spare
MOST_EXTRA_CHARS = 1000
_CHARS_PER_TOKEN = 3  # a cautious count: more tokens than text usually has, so the estimate is high
_MILLION = Decimal(1_000_000)
_MICRO = Decimal("0.000001")


def _preparer(operation: Operation) -> Callable[[Session, QuestionForAi], Prepared]:
    if operation is Operation.TAG:
        return tag.prepare
    if operation is Operation.SOLVE:
        return solve.prepare
    if operation is Operation.VERIFY:
        return verify.prepare
    raise Conflict(
        "This operation is not available yet.",
        code="AI_OPERATION_NOT_AVAILABLE",
        details={"operation": operation.value},
    )


# Operations whose result is only a suggestion: applied by an explicit click, never by the run.
ACCEPTORS: dict[Operation, ApplyStep] = {
    Operation.SOLVE: solve.accept,
    Operation.VERIFY: verify.accept,
}


@dataclass(frozen=True, slots=True)
class Candidate:
    row: AiModel
    provider: Provider
    api_key: str


@dataclass(frozen=True, slots=True)
class Attempt:
    candidate: Candidate
    outcome: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int | None = None
    result: StructuredResult | None = None


@dataclass(frozen=True, slots=True)
class Started:
    """Everything phase B and C need, carried out of phase A."""

    run_id: UUID
    organization_id: UUID
    prepared: Prepared
    question: QuestionForAi
    system: str
    user: str
    temperature: float | None
    chain: list[Candidate]


@dataclass(frozen=True, slots=True)
class RunView:
    run: AiRun
    attempts: list[AiRunAttempt]


def _cost(model: AiModel, tokens_in: int, tokens_out: int) -> Decimal | None:
    """Dollars for those tokens at the model's effective prices, or ``None`` if one is unknown."""
    prices = effective(model)
    if prices.price_in is None or prices.price_out is None:
        return None
    usd = (Decimal(tokens_in) * prices.price_in + Decimal(tokens_out) * prices.price_out) / _MILLION
    return usd.quantize(_MICRO, rounding=ROUND_UP)


def _estimate(chain: list[Candidate], system: str, user: str, max_out: int) -> Decimal | None:
    """The dearest model of the chain, so a fallback can never overspend the reservation. ``None``
    when no model of the chain has a known price."""
    tokens_in = math.ceil((len(system) + len(user)) / _CHARS_PER_TOKEN)
    known = [cost for c in chain if (cost := _cost(c.row, tokens_in, max_out)) is not None]
    return max(known) if known else None


def compose(instructions: str, values: dict[str, str], extra: str | None) -> tuple[str, str]:
    """The request's two parts. ``system`` is the locked safety preamble (and the person's extra
    instructions, which are instructions); ``user`` is the prompt, each value as a data block."""
    system = locked.SAFETY_PREAMBLE
    if extra:
        system += f"\n\nExtra instructions from the person running this:\n{extra}"
    return system, locked.render(instructions, values)


def _chain(
    session: Session,
    keyring: Keyring | None,
    organization_id: UUID,
    operation: Operation,
    chosen: UUID | None,
) -> list[Candidate]:
    """The model to try first and its fallbacks, each with the coaching's own key."""
    setting = session.scalars(
        select(OperationSetting).where(
            OperationSetting.organization_id == organization_id,
            OperationSetting.operation == operation.value,
        )
    ).first()
    first = chosen or (setting.default_model_id if setting is not None else None)
    if first is None:
        raise Conflict(
            "No model is chosen for this operation. An admin sets one under Admin, AI.",
            code="AI_NO_MODEL",
        )
    ids = [first]
    if setting is not None:
        ids += [m for m in (setting.fallback_1_id, setting.fallback_2_id) if m and m not in ids]
    keys: dict[Provider, str] = {}
    chain: list[Candidate] = []
    for position, model_id in enumerate(ids):
        try:
            row = usable_model(session, organization_id, model_id)
        except Conflict, ValidationFailed:
            if position == 0:
                raise  # the model asked for must work; a fallback that stopped working is skipped
            continue
        provider = Provider(row.provider)
        if provider not in keys:
            try:
                key = open_key(session, keyring, organization_id, provider)
            except KeyUnreadable:
                raise Conflict(
                    "The stored key could not be opened. An admin must enter it again.",
                    code="AI_KEY_UNREADABLE",
                ) from None
            if key is None:
                if position == 0:
                    raise Conflict(
                        f"No {provider.value.title()} key is stored. An admin adds one under"
                        " Admin, AI.",
                        code="AI_KEY_MISSING",
                    )
                continue
            keys[provider] = key
        chain.append(Candidate(row, provider, keys[provider]))
    return chain


def abandon_stale(session: Session, organization_id: UUID, user_id: UUID) -> int:
    """Close this person's runs that began long ago and never finished (a crash between the
    provider call and its record): failed, and the reserved budget given back."""
    cutoff = datetime.now(UTC) - STALE_AFTER
    stale = list(
        session.scalars(
            select(AiRun)
            .where(
                AiRun.organization_id == organization_id,
                AiRun.user_id == user_id,
                AiRun.status == "RUNNING",
                AiRun.started_at < cutoff,
            )
            .with_for_update(skip_locked=True)
        )
    )
    for run in stale:
        budget.release(session, organization_id=organization_id, run_id=run.id)
        run.status = "FAILED"
        run.error_code = "AI_RUN_ABANDONED"
        run.finished_at = datetime.now(UTC)
    session.flush()
    return len(stale)


def _start(
    session: Session,
    principal: Principal,
    keyring: Keyring | None,
    *,
    question_id: UUID,
    operation: Operation,
    extra_instructions: str | None,
    one_off_instructions: str | None,
    personal_prompt_id: UUID | None,
    model_id: UUID | None,
    test: bool,
) -> Started:
    """Steps 1 to 6: permission, inputs, prompt, model, estimate, and the budget reserved."""
    require(principal, Action.USE_AI)
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:
        raise NotFound("No such question.")
    if extra_instructions is not None and len(extra_instructions) > MOST_EXTRA_CHARS:
        raise ValidationFailed(
            f"Extra instructions can be at most {MOST_EXTRA_CHARS} characters.",
            code="AI_EXTRA_TOO_LONG",
        )
    question = read_for_ai(session, principal, question_id)
    if not test and not question.editable:
        raise Conflict(
            "This question cannot be edited now, so a result could not be applied. Run it as a"
            " test, or withdraw the question first.",
            code="AI_QUESTION_NOT_EDITABLE",
        )
    prepared = _preparer(operation)(session, question)
    resolved = prompts.resolve(
        session,
        organization_id=organization_id,
        user_id=principal.user_id,
        operation=operation,
        personal_template_id=personal_prompt_id,
        one_off=one_off_instructions,
    )
    system, user = compose(resolved.instructions, prepared.values, extra_instructions)
    chain = _chain(session, keyring, organization_id, operation, model_id)
    abandon_stale(session, organization_id, principal.user_id)
    run = AiRun(
        organization_id=organization_id,
        user_id=principal.user_id,
        question_id=question.question_id,
        operation=operation.value,
        mode=Mode.NOW.value,
        is_test=test,
        question_revision_id=question.revision_id,
        question_revision=question.revision,
        prompt_source=resolved.source,
        prompt_version_id=resolved.version_id,
        one_off_instructions=one_off_instructions,
        extra_instructions=extra_instructions,
        prompt_hash=hashlib.sha256(f"{system}\n{user}".encode()).hexdigest(),
        model_ref=chain[0].row.id,
    )
    session.add(run)
    session.flush()
    budget.reserve(
        session,
        organization_id=organization_id,
        user_id=principal.user_id,
        run_id=run.id,
        estimate_usd=_estimate(chain, system, user, prepared.max_output_tokens),
    )
    temperature = float(resolved.temperature) if resolved.temperature is not None else None
    return Started(run.id, organization_id, prepared, question, system, user, temperature, chain)


def _validate(
    prepared: Prepared, answer: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return prepared.check(answer), None
    except BadOutput:
        return None, "AI_OUTPUT_INVALID"


def _finish(
    session: Session,
    principal: Principal,
    started: Started,
    attempts: list[Attempt],
    *,
    test: bool,
    request_id: str | None,
) -> RunView:
    """Steps 8 to 10: validate, record, settle or release, apply."""
    run = session.scalars(select(AiRun).where(AiRun.id == started.run_id).with_for_update()).one()
    for position, attempt in enumerate(attempts, start=1):
        session.add(
            AiRunAttempt(
                organization_id=started.organization_id,
                run_id=run.id,
                position=position,
                model_ref=attempt.candidate.row.id,
                provider_model=attempt.candidate.row.model_id,
                outcome=attempt.outcome,
                tokens_in=attempt.tokens_in,
                tokens_out=attempt.tokens_out,
                latency_ms=attempt.latency_ms,
            )
        )
    answered = next((a for a in attempts if a.result is not None), None)
    run.finished_at = datetime.now(UTC)
    if answered is None or answered.result is None:
        run.status = "FAILED"
        run.error_code = f"AI_PROVIDER_{attempts[-1].outcome}"
        budget.release(session, organization_id=started.organization_id, run_id=run.id)
        session.flush()
        return _view(session, run)
    result = answered.result
    run.model_ref = answered.candidate.row.id
    run.answered_by = answered.candidate.row.model_id
    actual = result.cost_usd
    if actual is None and result.tokens_in is not None and result.tokens_out is not None:
        actual = _cost(answered.candidate.row, result.tokens_in, result.tokens_out)
    budget.settle(
        session, organization_id=started.organization_id, run_id=run.id, actual_usd=actual
    )
    output, problem = _validate(started.prepared, result.data)
    if output is None:
        run.status = "FAILED"
        run.error_code = problem
        session.flush()
        return _view(session, run)
    run.status = "SUCCEEDED"
    run.result = {"output": output, "before": started.prepared.before}
    if not test and started.prepared.apply is not None:
        base = RunBase(
            started.question.question_id, started.question.revision_id, started.question.revision
        )
        run.apply_status = started.prepared.apply(session, principal, base, output)
        if run.apply_status == "APPLIED":
            _audit_applied(session, principal, run, request_id)
    session.flush()
    return _view(session, run)


def _view(session: Session, run: AiRun) -> RunView:
    attempts = list(
        session.scalars(
            select(AiRunAttempt)
            .where(AiRunAttempt.run_id == run.id)
            .order_by(AiRunAttempt.position)
        )
    )
    return RunView(run, attempts)


def run_operation(
    database: Database,
    principal: Principal,
    keyring: Keyring | None,
    providers: ProviderFactory,
    *,
    question_id: UUID,
    operation: Operation,
    extra_instructions: str | None = None,
    one_off_instructions: str | None = None,
    personal_prompt_id: UUID | None = None,
    model_id: UUID | None = None,
    test: bool = False,
    request_id: str | None = None,
) -> RunView:
    """Run one operation on one question and return the finished run (it may have FAILED: a failed
    run is a result, with its error code, not an exception)."""
    with database.transaction(principal.tenant_context) as session:
        started = _start(
            session,
            principal,
            keyring,
            question_id=question_id,
            operation=operation,
            extra_instructions=extra_instructions,
            one_off_instructions=one_off_instructions,
            personal_prompt_id=personal_prompt_id,
            model_id=model_id,
            test=test,
        )
    attempts = _ask_models(started, providers)
    with database.transaction(principal.tenant_context) as session:
        return _finish(session, principal, started, attempts, test=test, request_id=request_id)


def _ask_models(started: Started, providers: ProviderFactory) -> list[Attempt]:
    attempts: list[Attempt] = []
    prepared = started.prepared
    for candidate in started.chain:
        request = StructuredRequest(
            model_id=candidate.row.model_id,
            system=started.system,
            user=started.user,
            schema_name=prepared.schema_name,
            schema=prepared.schema,
            max_output_tokens=prepared.max_output_tokens,
            temperature=started.temperature,
        )
        began = time.monotonic()
        try:
            result = providers(candidate.provider).generate_structured(candidate.api_key, request)
        except ProviderError as problem:
            attempts.append(
                Attempt(
                    candidate,
                    problem.kind.value,
                    latency_ms=round((time.monotonic() - began) * 1000),
                )
            )
            if problem.retryable:
                continue
            break
        attempts.append(
            Attempt(
                candidate,
                "OK",
                result.tokens_in,
                result.tokens_out,
                round((time.monotonic() - began) * 1000),
                result,
            )
        )
        break
    return attempts


def _may_see(principal: Principal, run: AiRun) -> bool:
    """A person sees their own runs; admins see everyone's (design note §5)."""
    return run.user_id == principal.user_id or is_allowed(principal, Action.MANAGE_AI_SETTINGS)


def get_run(session: Session, principal: Principal, run_id: UUID) -> RunView:
    require(principal, Action.USE_AI)
    run = session.get(AiRun, run_id)
    if run is None or not _may_see(principal, run):
        raise NotFound("No such run.")
    return _view(session, run)


def list_runs(session: Session, principal: Principal, question_id: UUID) -> list[RunView]:
    """The runs on a question, newest first: the person's own, or all of them for an admin. Someone
    who may not open the question gets "not found"."""
    require(principal, Action.USE_AI)
    read_for_ai(session, principal, question_id)
    query = select(AiRun).where(AiRun.question_id == question_id)
    if not is_allowed(principal, Action.MANAGE_AI_SETTINGS):
        query = query.where(AiRun.user_id == principal.user_id)
    runs = session.scalars(query.order_by(AiRun.started_at.desc()).limit(100))
    return [_view(session, run) for run in runs]


def _audit_applied(
    session: Session, principal: Principal, run: AiRun, request_id: str | None
) -> None:
    """A result that changed a question is written to the audit log (the run keeps the before)."""
    record_event(
        session,
        action="AI_RUN_APPLIED",
        entity_type="question",
        entity_id=run.question_id,
        organization_id=run.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        before=None,
        after={"run_id": str(run.id), "operation": run.operation},
    )


def apply_run(
    session: Session, principal: Principal, run_id: UUID, *, request_id: str | None
) -> RunView:
    """Apply a suggestion (a solved answer, a verify correction) after a person has seen it.

    Only to the exact revision the run read: if the question has changed since, the run becomes
    ``OUT_OF_DATE`` and nothing is written. The person applying must still be able to edit it."""
    require(principal, Action.USE_AI)
    run = session.scalars(select(AiRun).where(AiRun.id == run_id).with_for_update()).first()
    if run is None or not _may_see(principal, run):
        raise NotFound("No such run.")
    accept = ACCEPTORS.get(Operation(run.operation))
    if accept is None or run.is_test or run.status != "SUCCEEDED" or run.result is None:
        raise Conflict("This run has nothing to apply.", code="AI_RUN_NOT_APPLICABLE")
    if run.apply_status != "NOT_APPLIED":
        raise Conflict(
            "This run was already applied or can no longer be applied.",
            code="AI_RUN_NOT_APPLICABLE",
            details={"apply_status": run.apply_status},
        )
    output = run.result.get("output")
    if not isinstance(output, dict) or (
        run.operation == Operation.VERIFY.value and "corrected_content" not in output
    ):
        raise Conflict("This run suggests no change.", code="AI_RUN_NOT_APPLICABLE")
    base = RunBase(run.question_id, run.question_revision_id, run.question_revision)
    run.apply_status = accept(session, principal, base, output)
    if run.apply_status == "APPLIED":
        _audit_applied(session, principal, run, request_id)
    session.flush()
    return _view(session, run)
