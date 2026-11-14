"""Numbers for dashboards (Prometheus format), served on a separate port (ADR-0019).

The metrics port is not part of the public API: the web proxy forwards only ``/api/v1`` and
``/health``, and the compose file never publishes the port to the host. Labels are kept few and
bounded, so one busy day cannot create thousands of series: the route is the route *template*
(``/api/v1/questions/{id}``), never a raw path; ``organization_id`` appears only on the counters
for imports and jobs; user IDs, emails and request IDs are never labels.
"""

import threading
import time
from collections.abc import Awaitable, Callable, Iterable
from uuid import UUID

import structlog
from fastapi import FastAPI, Request, Response
from prometheus_client import REGISTRY, Counter, Histogram, start_http_server
from prometheus_client.core import GaugeMetricFamily, Metric
from prometheus_client.registry import Collector
from sqlalchemy import text
from sqlalchemy.pool import QueuePool

from qbank.core.db import Database
from qbank.core.tenancy import NO_CONTEXT

log = structlog.get_logger("qbank.metrics")

_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30)

HTTP_REQUESTS = Counter(
    "qbank_http_requests_total",
    "Requests answered, by route template and status class (2xx, 4xx, 5xx).",
    ["method", "route", "status_class"],
)
HTTP_LATENCY = Histogram(
    "qbank_http_request_duration_seconds",
    "Time to answer a request, by route template.",
    ["method", "route"],
    buckets=_LATENCY_BUCKETS,
)
LOGIN_ATTEMPTS = Counter(
    "qbank_login_attempts_total",
    "Sign-in attempts by method (password, google, link) and outcome; reason says why one failed.",
    ["method", "outcome", "reason"],
)
RATE_LIMITED = Counter(
    "qbank_rate_limited_total", "Requests refused by a rate limit, by limit.", ["scope"]
)
IMPORT_EVENTS = Counter(
    "qbank_import_events_total",
    "Syllabus import uploads and applies, per coaching, by event.",
    ["organization_id", "event"],
)
ASSET_EVENTS = Counter(
    "qbank_asset_events_total",
    "Picture uploads, per coaching, by event.",
    ["organization_id", "event"],
)
JOBS_FINISHED = Counter(
    "qbank_jobs_finished_total",
    "Background job attempts by type and outcome (succeeded, retried, failed, lease_lost).",
    ["job_type", "outcome", "organization_id"],
)
JOB_DURATION = Histogram(
    "qbank_job_duration_seconds",
    "How long a job handler ran, by type (successful attempts).",
    ["job_type"],
    buckets=_LATENCY_BUCKETS,
)


# A client may send any method token; only these become label values, the rest share "other", so
# the number of series stays fixed.
_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})


def method_label(method: str) -> str:
    return method if method in _METHODS else "other"


def org_label(organization_id: UUID | None) -> str:
    return str(organization_id) if organization_id else "platform"


def install_request_metrics(app: FastAPI) -> None:
    """Count and time every request. Install after the request logging, so it is outermost and
    also sees the 500 answer that logging produces for an unexpected error."""

    @app.middleware("http")
    async def request_metrics(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        route = str(getattr(request.scope.get("route"), "path", "unmatched"))
        method = method_label(request.method)
        HTTP_REQUESTS.labels(method, route, f"{response.status_code // 100}xx").inc()
        HTTP_LATENCY.labels(method, route).observe(time.perf_counter() - started)
        return response


class _PoolCollector(Collector):
    """Reads the connection pool when Prometheus asks, so the numbers are always current."""

    def __init__(self) -> None:
        self.database: Database | None = None

    def collect(self) -> Iterable[Metric]:
        pool = self.database.engine.pool if self.database else None
        if not isinstance(pool, QueuePool):
            return
        in_use = GaugeMetricFamily(
            "qbank_db_pool_connections", "Database connections by state.", labels=["state"]
        )
        in_use.add_metric(["in_use"], pool.checkedout())
        in_use.add_metric(["idle"], pool.checkedin())
        yield in_use
        size = GaugeMetricFamily("qbank_db_pool_size", "Connections the pool keeps open.")
        size.add_metric([], pool.size())
        yield size


class _JobQueueCollector(Collector):
    """Counts waiting and running jobs when Prometheus asks (the worker process only: the
    API's database role is not allowed to see other coachings' jobs)."""

    def __init__(self) -> None:
        self.database: Database | None = None

    def collect(self) -> Iterable[Metric]:
        if self.database is None:
            return
        try:
            with self.database.transaction(NO_CONTEXT) as session:
                rows = session.execute(text("SELECT * FROM jobs_stats()")).all()
        except Exception:  # the database is busy or restarting: skip this scrape, keep serving
            log.warning("job_queue_metrics_unavailable", exc_info=True)
            return
        depth = GaugeMetricFamily(
            "qbank_jobs_queue_depth",
            "Jobs waiting (QUEUED) or being worked on (RUNNING), by type.",
            labels=["job_type", "state"],
        )
        age = GaugeMetricFamily(
            "qbank_jobs_oldest_ready_age_seconds",
            "How long the oldest job that is ready to run has been waiting, by type.",
            labels=["job_type"],
        )
        for row in rows:
            depth.add_metric([row.job_type, row.state], row.jobs)
            if row.oldest_ready_age_seconds is not None:
                age.add_metric([row.job_type], row.oldest_ready_age_seconds)
        yield depth
        yield age


_pool_collector = _PoolCollector()
REGISTRY.register(_pool_collector)
_job_queue_collector = _JobQueueCollector()
REGISTRY.register(_job_queue_collector)


def watch_job_queue(database: Database) -> None:
    """Report the job queue from this process (the worker's, which may read the stats)."""
    _job_queue_collector.database = database


def watch_pool(database: Database) -> None:
    """Report this process's database pool (the most recently created one wins)."""
    _pool_collector.database = database


_server_lock = threading.Lock()
_serving_port: int | None = None


def start_metrics_server(port: int) -> None:
    """Serve ``/metrics`` on ``port`` in a background thread. Calling it again does nothing."""
    global _serving_port
    with _server_lock:
        if _serving_port is None:
            start_http_server(port)
            _serving_port = port
