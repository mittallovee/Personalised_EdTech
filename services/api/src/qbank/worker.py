"""Background worker process. Run with: ``python -m qbank.worker``."""

import signal
import sys
from types import FrameType

from qbank.core.config import get_settings
from qbank.core.db import Database
from qbank.core.jobs import JobRegistry, Worker
from qbank.core.logging import configure_logging
from qbank.core.metrics import start_metrics_server, watch_job_queue, watch_pool
from qbank.core.secretbox import Keyring
from qbank.core.storage import LocalDiskStorage, Storage
from qbank.core.telemetry import instrument_database, setup_tracing
from qbank.modules.ai.jobs import register_jobs as register_ai_jobs
from qbank.modules.ai.providers.registry import provider_for, use_demo_provider
from qbank.modules.health.jobs import register_jobs as register_health_jobs
from qbank.modules.ingestion.extract.job import register_jobs as register_extract_jobs
from qbank.modules.ingestion.public import SANDBOX_JOB_TYPES


def build_registry(
    ai_keyring: Keyring | None = None,
    *,
    database: Database | None = None,
    storage: Storage | None = None,
) -> JobRegistry:
    """Every module that has background jobs registers them here."""
    registry = JobRegistry()
    register_health_jobs(registry)
    register_ai_jobs(registry, ai_keyring)
    if database is not None and storage is not None:  # reading uploaded pages with AI (M6)
        register_extract_jobs(registry, database, ai_keyring, provider_for, storage)
    return registry


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level, service="worker", environment=settings.app_env.value)
    setup_tracing(settings, "worker")
    database = Database(settings.database_url)
    instrument_database(database.engine)
    watch_pool(database)
    watch_job_queue(database)
    if settings.metrics_port:
        start_metrics_server(settings.metrics_port)
    if settings.ai_demo_provider:
        use_demo_provider()
    registry = build_registry(
        settings.ai_keyring(),
        database=database,
        storage=LocalDiskStorage(settings.storage_dir),
    )
    worker = Worker(database, registry, skip_types=SANDBOX_JOB_TYPES)

    def request_stop(_signum: int, _frame: FrameType | None) -> None:
        worker.stop()  # finish the current job, then exit

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        worker.run_forever()
    finally:
        database.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
