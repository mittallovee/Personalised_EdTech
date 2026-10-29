# ADR-0019: Monitoring in practice: one log shape, traces, metrics, and a local opt-in stack
- Status: Proposed (owner approved the choices in chat on 29 Oct 2026; becomes Accepted when this PR is merged) · Date: 2026-10-29 · Requirements: K-06 (N-07) · Extends [ADR-0010](./0010-observability.md), within [ADR-0013](./0013-cloud-neutral-deployment.md)
## Context
ADR-0010 chose the tools (structlog, OpenTelemetry, Sentry) but little of it exists. Today the API writes one JSON line per
request with a request ID, jobs remember that ID, and `/health/*` exists. Missing: the same fields on every line
(organization, user, trace), logs from libraries in JSON, anything that follows a request from the browser through the API into
a job and its SQL, any metrics, any place to search logs or look at graphs, and a test that proves secrets stay out of logs.
(The M1 design note says OpenTelemetry and Sentry are "wired"; they are not; this PR corrects that sentence.)
The owner asked for: every event logged, any request traceable end to end, errors easy to find and fix, and relevant numbers
visible live. It must run on a Windows PC with Docker Desktop and stay cloud-neutral.
## Decision
1. **One log shape.** Every line is one JSON object: `timestamp`, `level`, `event` (a short `snake_case` name such as
   `login_failed`), `service` (`api`, `worker` or `web`), `env`, and, when known, `request_id`, `trace_id`, `span_id`,
   `organization_id`, `user_id`, `job_id`, `duration_ms`, `outcome`, plus fields specific to the event. Library logs (uvicorn,
   SQLAlchemy, Alembic) use the same shape. Logs go to stdout always (clouds collect that); when `OTEL_EXPORTER_OTLP_ENDPOINT` is
   set they are also sent to the collector through the same already-cleaned pipeline.
2. **IDs travel.** The web app makes (or forwards) `X-Request-ID` and the W3C `traceparent` header; the API binds
   `request_id`/`trace_id` at the start and `organization_id`/`user_id` once the caller is known; a job row stores the request ID
   and `traceparent`, so the worker continues the same trace. A failed request is traced by its `X-Request-ID` (shown in the error
   response): search logs for it, open the trace from any line.
3. **What is never logged** (the owner approved this list): passwords, session and CSRF tokens, activation and reset links,
   OAuth codes and secrets, API keys, `Authorization` and `Cookie` headers, request and response bodies, uploaded file contents,
   and any question, option, solution or other coaching content. Query strings are never logged (the path is logged as the route
   template, e.g. `/api/v1/questions/{id}`). No emails, names or phone numbers; people appear as `user_id`. The client IP appears only
   in security events (`login_failed`, rate limiting). Two layers enforce it: code logs identifiers, not content; and a redaction step
   in the log pipeline blanks forbidden field names and token-shaped values as a safety net. A test logs a bait value for each
   category and fails if any reaches the output (also checked on traces' attributes).
4. **Metrics** (Prometheus format, on a separate internal port so the public API and the web proxy never expose them): request
   count, errors and latency by method, route template and status class; database pool use; job queue depth, oldest-job age and
   outcomes by job type; login failures; import usage. `organization_id` is a label only on a few small counters (login failures, imports,
   job outcomes); `user_id`, request IDs and raw paths are never labels. Dashboards are for platform operators only, never for coaching users.
5. **Traces.** OpenTelemetry SDK in the API, worker and web, OTLP to a collector. Spans for HTTP requests, SQL (statement text with
   placeholders, never parameter values), outgoing HTTP calls, and each job. Everything off when no endpoint is configured, so
   tests and the plain compose stack are unchanged.
6. **Local stack, opt-in.** Compose profile `observability`: OpenTelemetry Collector, Tempo (traces), Loki (logs), Prometheus
   (metrics), Grafana (dashboards, provisioned from files). Retention: **7 days for logs and traces, 15 days for metrics**. Every port is
   bound to `127.0.0.1`; Grafana needs the admin password from the git-ignored `.env`, anonymous access is off. `docker compose up`
   without the profile starts none of it. Roughly 1.5 to 2 GB RAM while the profile runs.
7. **Error tracking.** No separate service for now: errors are searched in Loki, shown on a dashboard and recorded on traces. A Sentry-
   compatible hook, active only when `SENTRY_DSN` is set and with personal data sending off, is a later, separate PR.
8. **Out of scope here:** alert rules and service targets (K-13), AI cost and token metrics (M5), choosing a cloud's monitoring (M7).
## Delivery (one requirement per PR, each under about 400 lines)
K-06a logging foundation and the no-secrets test · K-06b metrics · K-06c tracing (one small migration: `traceparent` on `jobs`) ·
K-06d compose profile and data sources · K-06e dashboards and `docs/operations/observability.md`.
## Consequences
+ A problem can be followed from the browser request to the SQL and the job, and found by one ID. Open standards, so the same
code works with a cloud's monitoring at M7. Normal development stays light.
− About six more containers when the profile is on; one more column on `jobs`; the team must keep logging identifiers, not content.
## Alternatives considered
- **Elastic/OpenSearch stack:** heavier, more to run on a PC. · **Jaeger instead of Tempo:** also fine; Tempo shares Grafana's
  trace-to-logs links and needs one container. · **Reading Docker's log files (Promtail/Alloy with the Docker socket):** works only
  where there is a Docker socket; sending logs over OTLP behaves the same in any cloud. · **Sentry/GlitchTip now:** extra accounts or
  containers before there is real use; deferred (decision 7). · **Paid services (Datadog and similar):** cost and data leaves the PC.
