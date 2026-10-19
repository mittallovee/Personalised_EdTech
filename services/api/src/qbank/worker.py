"""Background worker process. Run with: ``python -m qbank.worker``."""

import signal
import sys
from types import FrameType

from qbank.core.config import get_settings
from qbank.core.db import Database
from qbank.core.jobs import JobRegistry, Worker
from qbank.core.logging import configure_logging
from qbank.modules.health.jobs import register_jobs as register_health_jobs


def build_registry() -> JobRegistry:
    """Every module that has background jobs registers them here."""
    registry = JobRegistry()
    register_health_jobs(registry)
    return registry


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    database = Database(settings.database_url)
    worker = Worker(database, build_registry())

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
