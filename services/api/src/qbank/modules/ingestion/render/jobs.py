"""The sandboxed worker's job: turn one original into pages (M6 6c/6d, design note §6).

The handler is idempotent: pages already written are skipped, a page is written once
(``(file, page number)`` is unique), and the pictures it stores have fixed keys, so a retry after a
crash makes nothing twice and loses nothing. A file that cannot be read ends ``FAILED`` with a
code, **not** as a job error (a job error would roll the state back); only a passing fault, such as
the storage being briefly unavailable, is raised so the job runs again.
"""

import contextlib
import time
from collections.abc import Iterable
from uuid import UUID

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from qbank.core.ids import new_id
from qbank.core.jobs import Job, JobHandler, JobRegistry, PermanentJobError
from qbank.core.storage import AlreadyExists, Missing, Storage
from qbank.modules.ingestion.models import IngestFile, IngestPage
from qbank.modules.ingestion.public import RENDER_JOB
from qbank.modules.ingestion.render import docx, images, pdf
from qbank.modules.ingestion.render.errors import RenderError
from qbank.modules.ingestion.render.limits import RENDER_SECONDS

log = structlog.get_logger("qbank.ingest")


def _keep(storage: Storage, key: str, data: bytes) -> None:
    with contextlib.suppress(AlreadyExists):  # a retry: the same page was stored before
        storage.put(key, data)


def _set_state(
    session: Session,
    file_id: UUID,
    state: str,
    *,
    error: str | None = None,
    pages: int | None = None,
) -> None:
    values: dict[str, object] = {"state": state, "error_code": error, "updated_at": func.now()}
    if pages is not None:
        values["page_count"] = pages
    session.execute(update(IngestFile).where(IngestFile.id == file_id).values(**values))


def _fail(session: Session, row: IngestFile, code: str, pages: int) -> None:
    log.warning("ingest_render_failed", code=code, kind=row.kind)
    _set_state(session, row.id, "FAILED", error=code, pages=pages)


def _store_page(
    session: Session, storage: Storage, row: IngestFile, page: pdf.RenderedPage
) -> None:
    base = f"org/{row.organization_id}/ingest-pages/{row.id}/{page.page_no}"
    image_key = thumb_key = None
    width = height = None
    if page.image is not None:
        image_key, thumb_key = base, f"{base}-t"
        _keep(storage, image_key, page.image.jpeg)
        _keep(storage, thumb_key, page.image.thumb)
        width, height = page.image.width, page.image.height
    figures = []
    for index, figure in enumerate(page.figures, start=1):
        key = f"{base}-f{index}"
        _keep(storage, key, figure.jpeg)
        figures.append({"key": key, "width": figure.width, "height": figure.height})
    session.execute(
        insert(IngestPage)
        .values(
            organization_id=row.organization_id,
            file_id=row.id,
            page_no=page.page_no,
            state="FAILED" if page.error else "READY",
            image_key=image_key,
            thumb_key=thumb_key,
            width=width,
            height=height,
            text=page.text,
            figures=figures,
            warnings=page.warnings,
            error_code=page.error,
            id=new_id(),
        )
        .on_conflict_do_nothing(index_elements=["file_id", "page_no"])
    )


def _pages(
    row: IngestFile, data: bytes, skip: set[int], deadline: float
) -> Iterable[pdf.RenderedPage]:
    """The pages of this original, by kind. Opening a document may raise ``RenderError``."""
    if row.kind == "PDF":
        document = pdf.open_pdf(data)
        return pdf.render_pages(document, skip=skip, deadline=deadline)
    if row.kind == "DOCX":
        return docx.read_pages(docx.open_docx(data), skip=skip)
    one = [] if 1 in skip else [pdf.RenderedPage(1, image=images.from_bytes(data))]
    return one


def render_handler(storage: Storage) -> JobHandler:
    def handle(session: Session, job: Job) -> None:
        try:
            file_id = UUID(str(job.payload.get("file_id")))
        except ValueError:
            raise PermanentJobError("the job names no file") from None
        row = session.scalars(select(IngestFile).where(IngestFile.id == file_id)).one_or_none()
        if row is None:
            raise PermanentJobError("no such file in this coaching")
        if row.state not in ("UPLOADED", "RENDERING"):
            return  # finished, failed, cancelled or already read: nothing to do (idempotent)
        _set_state(session, file_id, "RENDERING")
        try:
            data = storage.get(row.storage_key)
        except Missing:
            _set_state(session, file_id, "FAILED", error="ORIGINAL_MISSING")
            return
        done = set(session.scalars(select(IngestPage.page_no).where(IngestPage.file_id == file_id)))
        deadline = time.monotonic() + RENDER_SECONDS
        failed_pages = 0
        try:
            pages = iter(_pages(row, data, done, deadline))
        except RenderError as problem:
            _fail(session, row, problem.code, len(done))
            return
        while True:
            # Only reading the document is guarded as "the file is bad". Storing a page is not: a
            # storage fault is raised, so the job runs again, instead of blaming the file.
            try:
                page = next(pages, None)
            except RenderError as problem:
                _fail(session, row, problem.code, len(done))
                return
            except (
                Exception
            ):  # a hostile or broken file in a parser: only the fault's kind is logged
                _fail(session, row, "UNREADABLE_DOCUMENT", len(done))
                return
            if page is None:
                break
            state = session.scalar(select(IngestFile.state).where(IngestFile.id == file_id))
            if state == "CANCELLED":  # the person cancelled: keep what is made, start no more
                return
            _store_page(session, storage, row, page)
            failed_pages += 1 if page.error else 0
            done.add(page.page_no)
        if not done or failed_pages == len(done):
            _set_state(session, file_id, "FAILED", error="NO_READABLE_PAGE", pages=len(done))
            return
        _set_state(
            session,
            file_id,
            "READY",
            error="SOME_PAGES_FAILED" if failed_pages else None,
            pages=len(done),
        )

    return handle


def register_jobs(registry: JobRegistry, storage: Storage) -> None:
    registry.register(RENDER_JOB, render_handler(storage))
