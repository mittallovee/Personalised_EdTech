"""Routes to run an AI operation on a question and read its runs (M5 design note §6; H-04)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.secretbox import Keyring
from qbank.modules.ai import orchestrator
from qbank.modules.ai.schemas import RunAttemptOut, RunOut, RunsOut, StartRun

router = APIRouter(prefix="/api/v1", tags=["ai"])

_READ: dict[int | str, dict[str, Any]] = {404: {"description": "No such question or run"}}


def _out(view: orchestrator.RunView) -> RunOut:
    run = view.run
    return RunOut(
        id=run.id,
        question_id=run.question_id,
        operation=run.operation,
        status=run.status,
        apply_status=run.apply_status,
        is_test=run.is_test,
        requested_by=run.user_id,
        prompt_source=run.prompt_source,
        prompt_version_id=run.prompt_version_id,
        answered_by=run.answered_by,
        result=run.result,
        error_code=run.error_code,
        started_at=run.started_at,
        finished_at=run.finished_at,
        attempts=[
            RunAttemptOut(
                position=a.position,
                model=a.provider_model,
                outcome=a.outcome,
                tokens_in=a.tokens_in,
                tokens_out=a.tokens_out,
                latency_ms=a.latency_ms,
            )
            for a in view.attempts
        ],
    )


@router.post(
    "/questions/{question_id}/ai/runs",
    status_code=status.HTTP_201_CREATED,
    summary="Run an AI operation on a question (H-04, H-07)",
    description="Runs now and returns the finished run. **A run that failed is still a 201** with"
    " `status` FAILED and an `error_code`: the run is the record. The budget is reserved first and"
    " the request is refused with `AI_BUDGET_EXCEEDED` when it would pass the person's monthly"
    " budget. Tagging fills the chapter, topic, main concept, difficulty and Bloom level of the"
    " working revision, only if the question has not changed since the run began (otherwise"
    " `apply_status` is OUT_OF_DATE and nothing is written). `test` never writes.",
    responses={
        **_READ,
        409: {
            "description": "No model or key for the operation (`AI_NO_MODEL`,"
            " `AI_KEY_MISSING`), the budget is used up (`AI_BUDGET_EXCEEDED`), or the question"
            " cannot be edited"
        },
        422: {
            "description": "The question lacks what the operation needs (`AI_TAG_NEEDS_SUBJECT`)"
        },
    },
)
def start_run(
    question_id: UUID,
    body: StartRun,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> RunOut:
    keyring: Keyring | None = request.app.state.ai_keyring
    view = orchestrator.run_operation(
        database,
        principal,
        keyring,
        request.app.state.ai_providers,
        question_id=question_id,
        operation=body.operation,
        extra_instructions=body.extra_instructions,
        one_off_instructions=body.prompt,
        personal_prompt_id=body.personal_prompt_id,
        model_id=body.model_id,
        test=body.test,
        request_id=request.state.request_id,
    )
    return _out(view)


@router.get(
    "/questions/{question_id}/ai/runs",
    summary="The AI runs on a question (AI history)",
    description="The person's own runs on this question, newest first; admins see everyone's.",
    responses=_READ,
)
def list_runs(
    question_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> RunsOut:
    with database.transaction(principal.tenant_context) as session:
        return RunsOut(
            data=[_out(v) for v in orchestrator.list_runs(session, principal, question_id)]
        )


@router.get(
    "/ai/runs/{run_id}",
    summary="One AI run",
    description="The person's own run, or any run for an admin.",
    responses=_READ,
)
def get_run(
    run_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> RunOut:
    with database.transaction(principal.tenant_context) as session:
        return _out(orchestrator.get_run(session, principal, run_id))


@router.post(
    "/ai/runs/{run_id}/apply",
    summary="Apply a suggested answer or correction (H-09, H-10)",
    description="Applies what a solve or verify run suggested, after the person has seen old and"
    " new. Only to the exact revision the run read: if the question has changed since, the run"
    " becomes `OUT_OF_DATE` and nothing is written. The person must still be able to edit the"
    " question. Written to the audit log.",
    responses={
        **_READ,
        409: {"description": "The run has nothing to apply or was already settled"},
    },
)
def apply_run(
    run_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> RunOut:
    with database.transaction(principal.tenant_context) as session:
        return _out(
            orchestrator.apply_run(session, principal, run_id, request_id=request.state.request_id)
        )
