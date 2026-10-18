"""A trivial job used to check that the worker is alive and processing the queue."""

import structlog
from sqlalchemy.orm import Session

from qbank.core.jobs import Job, JobRegistry

log = structlog.get_logger("qbank.health")

PING = "health.ping"


def ping(_session: Session, job: Job) -> None:
    log.info("health_ping_processed", message=job.payload.get("message"))


def register_jobs(registry: JobRegistry) -> None:
    registry.register(PING, ping)
