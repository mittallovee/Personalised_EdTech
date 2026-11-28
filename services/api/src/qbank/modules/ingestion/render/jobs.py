"""The sandboxed worker's job handlers."""

from sqlalchemy.orm import Session

from qbank.core.jobs import Job, JobRegistry, PermanentJobError
from qbank.modules.ingestion.public import RENDER_JOB


def render_handler(session: Session, job: Job) -> None:
    del session, job
    raise PermanentJobError("rendering is not built yet")


def register_jobs(registry: JobRegistry) -> None:
    registry.register(RENDER_JOB, render_handler)
