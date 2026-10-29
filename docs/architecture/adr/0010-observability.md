# ADR-0010: Structured logs + OpenTelemetry + Sentry
- Status: Proposed · Date: 2026-10-18 · Extended by [ADR-0019](./0019-monitoring-stack-and-logging-rules.md)
## Decision
structlog JSON logs with request/job/org/user IDs; `X-Request-ID` on every response; OpenTelemetry instrumentation (FastAPI, SQLAlchemy, HTTP clients) exporting to a collector when configured; Sentry for errors when `SENTRY_DSN` set; `/health/live` and `/health/ready`. Cloud deployment (M7) sends these to the chosen cloud's monitoring or Grafana.
## Consequences
+ Problems are diagnosable from day one; vendor-neutral. − Small setup cost in M1.
