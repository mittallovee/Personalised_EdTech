"""Economy (batch) runs: handing a run to a provider's batch service and finishing it later (H-18).

The five guarantees of ADR-0009 and where each is kept:

1. **At most one submission.** ``claim_submit`` moves a run ``QUEUED`` to ``SUBMITTING`` with one
   conditional UPDATE, so one worker wins; only then is the ``ai.submit_batch`` job queued. That job
   calls ``submit_batch`` only on its very first attempt. Any later attempt (a retry after an
   error, or another worker after a lost lease) never submits: it looks the batch up by the run's id
   (``find_batches_by_tag``) and adopts it, or, after the last attempt, gives up as
   ``SUBMISSION_UNKNOWN``. A cancel never submits either.
2. **Every ending settles the reservation.** A result replaces it with the real (discounted) cost; a
   failed, expired or cancelled batch gives it back; ``SUBMISSION_UNKNOWN`` keeps all of it held
   until
   an admin resolves the run, so a possibly-running batch is never undercounted.
3. **Cancelling is final for applying.** The intent is recorded first; a result that still arrives
   is stored and charged and never applied.
4. **Authorisation at apply time (B-10).** The requester is loaded again; if they can no longer use
   the coaching the result is kept as ``NEEDS_REVIEW``; the question's revision is checked as
   always.
5. **Restart-safe and idempotent.** Every handler first looks at the run's status and does nothing
   when it is not the state that handler works on.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import AppError, Conflict, NotFound
from qbank.core.jobs import Job, JobHandler, PermanentJobError, enqueue
from qbank.core.permissions import Action, require
from qbank.core.secretbox import Keyring, KeyUnreadable
from qbank.modules.ai import budget
from qbank.modules.ai.keys import open_key
from qbank.modules.ai.models import AiModel, AiRun
from qbank.modules.ai.names import Mode, Operation, Provider
from qbank.modules.ai.operations.base import PrepareContext, RunBase
from qbank.modules.ai.orchestrator import (
    COLLECT_BATCH,
    FIRST_COLLECT_AFTER,
    PREPARERS,
    SUBMIT_BATCH,
    SUBMIT_JOB_ATTEMPTS,
    Attempt,
    Candidate,
    ProviderFactory,
    RunView,
    _cost,
    _may_see,
    _view,
    conclude,
)
from qbank.modules.ai.providers.base import (
    BatchProvider,
    BatchState,
    ProviderError,
    ProviderErrorKind,
    StructuredRequest,
)
from qbank.modules.audit.public import record_event
from qbank.modules.identity.public import principal_for
from qbank.modules.notifications.public import notify
from qbank.modules.organizations.public import admin_user_ids
from qbank.modules.questions.public import QuestionForAi

log = structlog.get_logger("qbank.ai")

GIVE_UP_AFTER = timedelta(hours=48)  # providers promise results within 24 hours
# A provider that answered "no" to a submission did not create a batch, so it is safe to say so.
# Anything else (a timeout, an outage, an unreadable answer) may have created one: look it up.
_DEFINITE_REFUSALS = frozenset(
    {
        ProviderErrorKind.AUTH,
        ProviderErrorKind.BAD_REQUEST,
        ProviderErrorKind.TOO_LARGE,
        ProviderErrorKind.RATE_LIMITED,
    }
)


class NotVisibleYet(Exception):
    """The provider does not show the batch yet; the job is tried again later."""


def _run(session: Session, run_id: object) -> AiRun | None:
    try:
        wanted = UUID(str(run_id))
    except ValueError:
        return None
    return session.scalars(select(AiRun).where(AiRun.id == wanted).with_for_update()).first()


def _adapter(providers: ProviderFactory, provider: Provider) -> BatchProvider:
    adapter = providers(provider)
    if not isinstance(adapter, BatchProvider):  # cannot happen: Economy was checked at the start
        raise PermanentJobError("this provider has no batch service")
    return adapter


def _key(session: Session, keyring: Keyring | None, run: AiRun, model: AiModel) -> str | None:
    try:
        return open_key(session, keyring, run.organization_id, Provider(model.provider))
    except KeyUnreadable:
        return None


def _tell_requester(session: Session, run: AiRun) -> None:
    notify(
        session,
        organization_id=run.organization_id,
        user_id=run.user_id,
        kind="AI_RUN_FINISHED",
        data={
            "run_id": str(run.id),
            "question_id": str(run.question_id),
            "operation": run.operation,
            "status": run.status,
            "apply_status": run.apply_status,
        },
    )


def _end_without_answer(session: Session, run: AiRun, status: str, code: str) -> None:
    """The batch ended with nothing to use (failed, expired, cancelled): no charge, so the
    reservation is given back."""
    run.status = status
    run.error_code = code
    run.finished_at = datetime.now(UTC)
    budget.release(session, organization_id=run.organization_id, run_id=run.id)
    session.flush()
    _tell_requester(session, run)


# --- 1. Claim ---------------------------------------------------------------------------------


def claim_submit(session: Session, job: Job) -> None:
    """Move a run from QUEUED to SUBMITTING, once, and only then queue the submit job."""
    try:
        run_id = UUID(str(job.payload.get("run_id")))
    except ValueError:
        raise PermanentJobError("the job names no run") from None
    won = session.execute(
        update(AiRun)
        .where(AiRun.id == run_id, AiRun.status == "QUEUED")
        .values(status="SUBMITTING", submit_started_at=datetime.now(UTC))
        .returning(AiRun.id)
    ).first()
    if won is None:  # cancelled while it waited, or claimed by another job already
        return
    enqueue(
        session,
        SUBMIT_BATCH,
        {"run_id": str(run_id)},
        context=job.tenant_context,
        request_id=job.request_id,
        max_attempts=SUBMIT_JOB_ATTEMPTS,
    )


# --- 2. Submit (or, on any later attempt, reconcile) ----------------------------------------------


def _adopt(
    session: Session,
    run: AiRun,
    job: Job,
    batch_id: str,
    adapter: BatchProvider,
    api_key: str,
) -> None:
    run.provider_batch_id = batch_id
    run.status = "SUBMITTED"
    session.flush()
    if run.cancel_requested_at is not None:  # cancelled while it was being handed over
        try:
            adapter.cancel_batch(api_key, batch_id)
        except ProviderError:
            log.warning("ai_batch_cancel_failed", run_id=str(run.id))
    enqueue(
        session,
        COLLECT_BATCH,
        {"run_id": str(run.id)},
        context=job.tenant_context,
        request_id=job.request_id,
        delay_seconds=FIRST_COLLECT_AFTER,
        max_attempts=3,
    )


def submit_handler(keyring: Keyring | None, providers: ProviderFactory) -> JobHandler:
    def handle(session: Session, job: Job) -> None:
        run = _run(session, job.payload.get("run_id"))
        if run is None or run.status != "SUBMITTING" or run.provider_batch_id is not None:
            return
        model = session.get(AiModel, run.model_ref) if run.model_ref else None
        key = _key(session, keyring, run, model) if model is not None else None
        if model is None or key is None or run.request is None:
            _end_without_answer(session, run, "FAILED", "AI_KEY_UNREADABLE")
            return
        adapter = _adapter(providers, Provider(model.provider))
        tag = str(run.id)
        if job.attempts <= 1:  # the only attempt that may submit
            request = StructuredRequest(
                model_id=model.model_id,
                system=run.request["system"],
                user=run.request["user"],
                schema_name=run.request["schema_name"],
                schema=run.request["schema"],
                max_output_tokens=run.request["max_output_tokens"],
                temperature=run.request["temperature"],
            )
            try:
                batch_id = adapter.submit_batch(key, tag=tag, request=request)
            except ProviderError as problem:
                if problem.kind in _DEFINITE_REFUSALS:
                    _end_without_answer(session, run, "FAILED", f"AI_PROVIDER_{problem.kind.value}")
                    return
                raise  # it may have been accepted: the next attempt looks it up, never re-sends
            _adopt(session, run, job, batch_id, adapter, key)
            return
        found = adapter.find_batches_by_tag(key, tag)
        if found:
            _adopt(session, run, job, found[0], adapter, key)
            return
        if job.attempts < job.max_attempts:
            raise NotVisibleYet
        # The provider's visibility window has passed with no sign of it: the outcome is unknown.
        # The whole reservation stays held until an admin resolves the run.
        run.status = "SUBMISSION_UNKNOWN"
        run.finished_at = datetime.now(UTC)
        session.flush()
        _tell_requester(session, run)
        for admin in admin_user_ids(session, run.organization_id):
            notify(
                session,
                organization_id=run.organization_id,
                user_id=admin,
                kind="AI_SUBMISSION_UNKNOWN",
                data={"run_id": str(run.id), "question_id": str(run.question_id)},
            )

    return handle


# --- 3. Collect -----------------------------------------------------------------------------------


def _later(run: AiRun) -> float:
    """Seconds until the provider is asked again: often at first, hourly after a long wait."""
    waited = datetime.now(UTC) - (run.submit_started_at or run.started_at)
    if waited < timedelta(minutes=10):
        return 60.0
    if waited < timedelta(hours=1):
        return 300.0
    return 3600.0


def _ask_again(session: Session, run: AiRun, job: Job) -> None:
    enqueue(
        session,
        COLLECT_BATCH,
        {"run_id": str(run.id)},
        context=job.tenant_context,
        request_id=job.request_id,
        delay_seconds=_later(run),
        max_attempts=3,
    )


def _snapshot(run: AiRun) -> QuestionForAi | None:
    saved = (run.request or {}).get("question")
    if not isinstance(saved, dict):
        return None
    return QuestionForAi(
        question_id=run.question_id,
        revision_id=run.question_revision_id,
        revision=run.question_revision,
        version_number=saved["version_number"],
        editable=True,
        content=saved["content"],
        text=saved["text"],
        metadata=saved["metadata"],
    )


def collect_handler(keyring: Keyring | None, providers: ProviderFactory) -> JobHandler:
    def handle(session: Session, job: Job) -> None:
        run = _run(session, job.payload.get("run_id"))
        if run is None or run.status != "SUBMITTED" or run.provider_batch_id is None:
            return
        model = session.get(AiModel, run.model_ref) if run.model_ref else None
        key = _key(session, keyring, run, model) if model is not None else None
        if model is None or key is None:
            _end_without_answer(session, run, "FAILED", "AI_KEY_UNREADABLE")
            return
        if datetime.now(UTC) - (run.submit_started_at or run.started_at) > GIVE_UP_AFTER:
            _end_without_answer(session, run, "EXPIRED", "AI_PROVIDER_BATCH_EXPIRED")
            return
        adapter = _adapter(providers, Provider(model.provider))
        try:
            state = adapter.batch_status(key, run.provider_batch_id)
            answer = (
                adapter.fetch_batch_answer(key, run.provider_batch_id, tag=str(run.id))
                if state is BatchState.DONE
                else None
            )
        except ProviderError as problem:
            if problem.kind is ProviderErrorKind.AUTH:
                _end_without_answer(session, run, "FAILED", "AI_PROVIDER_AUTH")
            else:
                _ask_again(session, run, job)
            return
        if state is BatchState.IN_PROGRESS:
            _ask_again(session, run, job)
            return
        cancelled = run.cancel_requested_at is not None
        if state is BatchState.CANCELLED:
            _end_without_answer(session, run, "CANCELLED", "AI_RUN_CANCELLED")
            return
        if state in (BatchState.FAILED, BatchState.EXPIRED) or answer is None:
            expired = state is BatchState.EXPIRED
            _end_without_answer(
                session,
                run,
                "CANCELLED" if cancelled else "EXPIRED" if expired else "FAILED",
                "AI_PROVIDER_BATCH_EXPIRED" if expired else "AI_PROVIDER_BATCH_FAILED",
            )
            return
        candidate = Candidate(model, Provider(model.provider), "")
        if answer.result is None:
            attempt = Attempt(candidate, (answer.error or ProviderErrorKind.BAD_OUTPUT).value)
        else:
            attempt = Attempt(
                candidate,
                "OK",
                answer.result.tokens_in,
                answer.result.tokens_out,
                None,
                answer.result,
            )
        question = _snapshot(run)
        principal = principal_for(session, run.user_id)  # B-10: who they are now
        try:
            if question is None:
                raise NotFound("the question snapshot is missing")
            prepared = PREPARERS[Operation(run.operation)](
                session,
                question,
                PrepareContext(run.organization_id, (run.request or {}).get("target_language")),
            )
        except AppError:
            # The result cannot be checked any more (the lists it refers to changed). It was
            # still paid for, so charge it, and keep nothing.
            _charge_and_fail(session, run, attempt, "AI_RESULT_UNCHECKABLE")
            _tell_requester(session, run)
            return
        base = RunBase(run.question_id, run.question_revision_id, run.question_revision)
        conclude(session, principal, run, prepared, base, [attempt], request_id=job.request_id)
        _tell_requester(session, run)

    return handle


def _charge_and_fail(session: Session, run: AiRun, attempt: Attempt, code: str) -> None:
    result = attempt.result
    actual = None
    if result is not None and result.tokens_in is not None and result.tokens_out is not None:
        actual = _cost(
            attempt.candidate.row, result.tokens_in, result.tokens_out, run.batch_discount
        )
    if result is not None:
        budget.settle(
            session, organization_id=run.organization_id, run_id=run.id, actual_usd=actual
        )
    else:
        budget.release(session, organization_id=run.organization_id, run_id=run.id)
    run.status = "CANCELLED" if run.cancel_requested_at is not None else "FAILED"
    run.error_code = code
    run.finished_at = datetime.now(UTC)
    session.flush()


# --- Cancel and resolve ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CancelCall:
    """What the route must still do after the intent is recorded: ask the provider to stop. The key
    is held in memory for that one call and never stored or returned."""

    provider: Provider
    api_key: str
    batch_id: str


def cancel_run(
    session: Session,
    principal: Principal,
    keyring: Keyring | None,
    run_id: UUID,
    *,
    request_id: str | None,
) -> tuple[RunView, CancelCall | None]:
    """Cancel an Economy run while it waits.

    Before it is handed to the provider it simply ends. After that only the *intent* is recorded
    here (the provider is asked to stop afterwards, and may be too late): whatever result still
    arrives is kept and charged but never applied."""
    require(principal, Action.USE_AI)
    run = _run(session, run_id)
    if run is None or not _may_see(principal, run):
        raise NotFound("No such run.")
    if run.mode != Mode.ECONOMY.value or run.status not in ("QUEUED", "SUBMITTING", "SUBMITTED"):
        raise Conflict(
            "Only an Economy run that is still waiting can be cancelled.",
            code="AI_RUN_NOT_CANCELLABLE",
            details={"status": run.status},
        )
    if run.cancel_requested_at is None:
        run.cancel_requested_at = datetime.now(UTC)
        record_event(
            session,
            action="AI_RUN_CANCELLED",
            entity_type="question",
            entity_id=run.question_id,
            organization_id=run.organization_id,
            actor_user_id=principal.user_id,
            actor_is_platform=principal.acting_organization_id is not None,
            request_id=request_id,
            after={"run_id": str(run.id), "was": run.status},
        )
    if run.status == "QUEUED":
        run.status = "CANCELLED"
        run.error_code = "AI_RUN_CANCELLED"
        run.finished_at = datetime.now(UTC)
        budget.release(session, organization_id=run.organization_id, run_id=run.id)
    session.flush()
    call: CancelCall | None = None
    if run.status == "SUBMITTED" and run.provider_batch_id is not None and run.model_ref:
        model = session.get(AiModel, run.model_ref)
        key = _key(session, keyring, run, model) if model is not None else None
        if model is not None and key is not None:
            call = CancelCall(Provider(model.provider), key, run.provider_batch_id)
    return _view(session, run), call


def ask_provider_to_stop(providers: ProviderFactory, call: CancelCall) -> None:
    """Best effort, after the cancel was recorded. A failure changes nothing: the intent stands, so
    the result can never be applied."""
    try:
        _adapter(providers, call.provider).cancel_batch(call.api_key, call.batch_id)
    except ProviderError, PermanentJobError:
        log.warning("ai_batch_cancel_failed", provider=call.provider.value)


def resolve_unknown(
    session: Session,
    principal: Principal,
    run_id: UUID,
    *,
    actual_usd: Decimal | None,
    request_id: str | None,
) -> RunView:
    """An admin settles a run whose submission outcome was never learned, after reading the
    provider's own billing: ``actual_usd`` is what it cost (``None``: it cost nothing). Until then
    the whole reservation stays held."""
    require(principal, Action.MANAGE_AI_SETTINGS)
    run = _run(session, run_id)
    if run is None:
        raise NotFound("No such run.")
    if run.status != "SUBMISSION_UNKNOWN":
        raise Conflict(
            "Only a run whose submission is unknown needs this.", code="AI_RUN_NOT_UNKNOWN"
        )
    if actual_usd is None:
        budget.release(session, organization_id=run.organization_id, run_id=run.id)
    else:
        budget.settle(
            session, organization_id=run.organization_id, run_id=run.id, actual_usd=actual_usd
        )
    run.status = "FAILED"
    run.error_code = "AI_SUBMISSION_UNKNOWN"
    run.finished_at = datetime.now(UTC)
    record_event(
        session,
        action="AI_RUN_RESOLVED",
        entity_type="question",
        entity_id=run.question_id,
        organization_id=run.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=principal.acting_organization_id is not None,
        request_id=request_id,
        after={
            "run_id": str(run.id),
            "actual_usd": None if actual_usd is None else format(actual_usd, "f"),
        },
    )
    session.flush()
    return _view(session, run)
