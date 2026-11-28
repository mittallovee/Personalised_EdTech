"""The sandboxed document worker. Run with: ``python -m qbank.ingest_worker`` (ADR-0024, K-17).

It takes only document-rendering jobs, with a database role of its own, and runs in a container
with no network, a read-only filesystem and capped resources (see ``compose.yaml``). It is the only
place a document is opened.
"""

import signal
import sys
from types import FrameType

from qbank.core.config import get_settings
from qbank.core.db import Database
from qbank.core.jobs import JobRegistry, Worker
from qbank.core.logging import configure_logging
from qbank.core.storage import LocalDiskStorage, Storage
from qbank.modules.ingestion.public import SANDBOX_JOB_TYPES
from qbank.modules.ingestion.render.jobs import register_jobs


def build_registry(storage: Storage) -> JobRegistry:
    registry = JobRegistry()
    register_jobs(registry, storage)
    return registry


def main() -> int:
    settings = get_settings()
    configure_logging(
        settings.log_level, service="ingest-worker", environment=settings.app_env.value
    )
    database = Database(settings.database_url)
    worker = Worker(
        database,
        build_registry(LocalDiskStorage(settings.storage_dir)),
        only_types=SANDBOX_JOB_TYPES,
    )

    def request_stop(_signum: int, _frame: FrameType | None) -> None:
        worker.stop()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        worker.run_forever()
    finally:
        database.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
