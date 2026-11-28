"""The job that reads a file's pages with AI, one page at a time (M6 6f, G-03, G-04, N-05).

Runs in the normal worker, which holds the AI keys (the sandboxed render worker holds none). A page
is three short steps, never one long transaction, so nothing is held while a provider thinks:

    1  a transaction: the page is marked running and its cost reserved against the person's budget
    2  no transaction: the provider is asked, with the page picture and its text
    3  a transaction: the cost is settled, the candidates are written, the page is marked done

A crash between 1 and 3 leaves a page marked running with a reservation: the next attempt gives the
reservation back and reads the page again. A candidate has a unique ``(run, page, ordinal)``, so a
page is never written twice. The pages of a cancelled file are simply not started.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from qbank.core.db import Database
from qbank.core.errors import AppError
from qbank.core.ids import new_id
from qbank.core.jobs import Job, JobHandler, JobRegistry, PermanentJobError
from qbank.core.secretbox import Keyring
from qbank.core.storage import Missing, Storage
from qbank.modules.ai.public import (
    ProviderFactory,
    make_call,
    release_reservation,
    reserve_call,
    settle_call,
)
from qbank.modules.ingestion.extract import prompt
from qbank.modules.ingestion.extract.schema import BadPage, read_page
from qbank.modules.ingestion.models import (
    IngestCandidate,
    IngestFile,
    IngestPage,
    IngestRun,
    IngestRunPage,
)
from qbank.modules.ingestion.public import EXTRACT_JOB
from qbank.modules.notifications.public import notify

log = structlog.get_logger("qbank.ingest")


@dataclass(frozen=True, slots=True)
class _Page:
    page_no: int
    image_key: str | None
    text: str | None
    figure_keys: tuple[str, ...]


def _finish(
    database: Database, job: Job, run_id: UUID, *, state: str, error: str | None = None
) -> None:
    """Close the run and the file, and tell the person."""
    with database.transaction(job.tenant_context) as session:
        run = session.get(IngestRun, run_id)
        if run is None or run.state != "RUNNING":
            return
        run.state, run.error_code, run.finished_at = state, error, datetime.now(UTC)
        file = session.get(IngestFile, run.file_id)
        if file is not None and file.state == "EXTRACTING":
            file.state = {"DONE": "DONE", "PARTIAL": "PARTIAL", "CANCELLED": "CANCELLED"}.get(
                state, "FAILED"
            )
            file.error_code = error
            file.updated_at = func.now()
        found = (
            session.scalar(
                select(func.count())
                .select_from(IngestCandidate)
                .where(IngestCandidate.run_id == run_id)
            )
            or 0
        )
        if state != "CANCELLED":
            notify(
                session,
                organization_id=run.organization_id,
                user_id=run.requested_by,
                kind="INGEST_EXTRACTED",
                data={
                    "file_id": str(run.file_id),
                    "state": state,
                    "candidates": found,
                    "pages_failed": run.pages_failed,
                },
            )


def _who(job: Job) -> tuple[UUID, UUID]:
    """The coaching and the person a job works for, as the API recorded them when it queued it."""
    if job.organization_id is None or job.created_by is None:
        raise PermanentJobError("the job has no coaching or person")
    return job.organization_id, job.created_by


def _cancelled(database: Database, job: Job, run_id: UUID) -> bool:
    with database.transaction(job.tenant_context) as session:
        run = session.get(IngestRun, run_id)
        file = session.get(IngestFile, run.file_id) if run is not None else None
        return run is None or run.state != "RUNNING" or file is None or file.state == "CANCELLED"


def extract_handler(
    database: Database, keyring: Keyring | None, providers: ProviderFactory, storage: Storage
) -> JobHandler:
    def handle(_session: object, job: Job) -> None:
        try:
            run_id = UUID(str(job.payload.get("run_id")))
        except ValueError:
            raise PermanentJobError("the job names no run") from None
        organization_id, _user = _who(job)
        reuse: dict[int, UUID] = {}
        with database.transaction(job.tenant_context) as session:
            run = session.get(IngestRun, run_id)
            if run is None:
                raise PermanentJobError("no such run in this coaching")
            if run.state != "RUNNING":
                return  # finished or cancelled: nothing to do (idempotent)
            model_ref, file_id = run.model_ref, run.file_id
            done = {
                row.page_no: row
                for row in session.scalars(
                    select(IngestRunPage).where(IngestRunPage.run_id == run_id)
                )
            }
            pages = [
                _Page(
                    p.page_no,
                    p.image_key,
                    p.text,
                    tuple(str(f["key"]) for f in (p.figures or []) if isinstance(f, dict)),
                )
                for p in session.scalars(
                    select(IngestPage)
                    .where(IngestPage.file_id == file_id, IngestPage.state == "READY")
                    .order_by(IngestPage.page_no)
                )
            ]
            # A page a dead attempt left running: its reservation goes back, and the same row is
            # used again when the page is read (the table is append-only: nothing is deleted).
            for row in done.values():
                if row.state == "RUNNING":
                    release_reservation(
                        session, organization_id=organization_id, run_id=row.ledger_id
                    )
                    reuse[row.page_no] = row.id
        stopped: str | None = None
        for page in pages:
            existing = done.get(page.page_no)
            if existing is not None and existing.state in ("DONE", "FAILED"):
                continue
            if _cancelled(database, job, run_id):
                _finish(database, job, run_id, state="CANCELLED")
                return
            stopped = _read_one(
                database,
                job,
                keyring,
                providers,
                storage,
                run_id,
                model_ref,
                page,
                reuse.get(page.page_no),
            )
            if stopped is not None:
                break
        with database.transaction(job.tenant_context) as session:
            counted = session.get(IngestRun, run_id)
            failed = counted.pages_failed if counted is not None else 0
            finished = counted.pages_done if counted is not None else 0
        if stopped is not None:
            _finish(database, job, run_id, state="PARTIAL" if finished else "FAILED", error=stopped)
        elif finished == 0:
            _finish(database, job, run_id, state="FAILED", error="NO_PAGE_READ")
        else:
            _finish(database, job, run_id, state="PARTIAL" if failed else "DONE")

    return handle


def _read_one(
    database: Database,
    job: Job,
    keyring: Keyring | None,
    providers: ProviderFactory,
    storage: Storage,
    run_id: UUID,
    model_ref: UUID,
    page: _Page,
    reuse_row_id: UUID | None,
) -> str | None:
    """Read one page. Returns a code when the whole run must stop (budget, key, model)."""
    organization_id, user_id = _who(job)
    pictures: list[bytes] = []
    try:
        for key in (page.image_key, *page.figure_keys):
            if key is not None:
                pictures.append(storage.get(key))
    except Missing:
        _mark(database, job, run_id, page.page_no, failed="PICTURE_MISSING")
        return None
    request = prompt.build_request(
        model_id="", page_no=page.page_no, text=page.text, pictures=tuple(pictures)
    )
    page_row_id, ledger_id = reuse_row_id or new_id(), new_id()
    with database.transaction(job.tenant_context) as session:
        try:
            call = reserve_call(
                session,
                keyring,
                organization_id=organization_id,
                user_id=user_id,
                model_id=model_ref,
                request=request,
                run_id=ledger_id,
                needs_pictures=bool(pictures),
            )
        except AppError as problem:
            return problem.code  # budget used up, no key, model not usable: stop the run
        if reuse_row_id is None:
            session.add(
                IngestRunPage(
                    id=page_row_id,
                    organization_id=organization_id,
                    run_id=run_id,
                    page_no=page.page_no,
                    state="RUNNING",
                    ledger_id=ledger_id,
                )
            )
        else:
            session.execute(
                update(IngestRunPage)
                .where(IngestRunPage.id == page_row_id)
                .values(ledger_id=ledger_id, started_at=func.now())
            )
    request = prompt.build_request(
        model_id=call.model.model_id,
        page_no=page.page_no,
        text=page.text,
        pictures=tuple(pictures),
    )
    outcome = make_call(call, providers, request)
    with database.transaction(job.tenant_context) as session:
        settle_call(session, call, outcome)
        error: str | None = None
        count = 0
        data: dict[str, Any] | None = outcome.result.data if outcome.result is not None else None
        if data is None:
            error = f"AI_PROVIDER_{outcome.failure}"
        else:
            try:
                reading = read_page(data)
            except BadPage:
                error = "AI_OUTPUT_INVALID"
            else:
                file_id = session.scalar(select(IngestRun.file_id).where(IngestRun.id == run_id))
                for candidate in reading.candidates:
                    session.execute(
                        insert(IngestCandidate)
                        .values(
                            id=new_id(),
                            organization_id=organization_id,
                            file_id=file_id,
                            run_id=run_id,
                            page_no=page.page_no,
                            ordinal=candidate.ordinal,
                            region=candidate.region,
                            raw=candidate.raw,
                            content=candidate.content,
                            findings=candidate.findings,
                            confidence=candidate.confidence,
                            warnings=candidate.warnings,
                        )
                        .on_conflict_do_nothing(index_elements=["run_id", "page_no", "ordinal"])
                    )
                count = len(reading.candidates)
        _close_page(session, page_row_id, run_id, error, count)
    return None


def _close_page(
    session: Any, page_row_id: UUID, run_id: UUID, error: str | None, count: int
) -> None:
    session.execute(
        update(IngestRunPage)
        .where(IngestRunPage.id == page_row_id)
        .values(
            state="FAILED" if error else "DONE",
            error_code=error,
            candidate_count=count,
            finished_at=func.now(),
        )
    )
    session.execute(
        update(IngestRun)
        .where(IngestRun.id == run_id)
        .values(
            pages_done=IngestRun.pages_done + (0 if error else 1),
            pages_failed=IngestRun.pages_failed + (1 if error else 0),
        )
    )


def _mark(database: Database, job: Job, run_id: UUID, page_no: int, *, failed: str) -> None:
    organization_id, _user = _who(job)
    with database.transaction(job.tenant_context) as session:
        row_id = new_id()
        session.add(
            IngestRunPage(
                id=row_id,
                organization_id=organization_id,
                run_id=run_id,
                page_no=page_no,
                state="RUNNING",
                ledger_id=new_id(),
            )
        )
        session.flush()
        _close_page(session, row_id, run_id, failed, 0)


def register_jobs(
    registry: JobRegistry,
    database: Database,
    keyring: Keyring | None,
    providers: ProviderFactory,
    storage: Storage,
) -> None:
    registry.register(EXTRACT_JOB, extract_handler(database, keyring, providers, storage))
