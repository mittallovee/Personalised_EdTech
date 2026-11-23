# Watching the app: logs, traces and live graphs

> Requirement **K-06** (N-07) · Decision: [ADR-0019](../architecture/adr/0019-monitoring-stack-and-logging-rules.md)
> Not included yet: alert rules and written service targets (**K-13**), and an error-tracking service
> (Sentry or similar: a later, optional step; today errors are found in the logs, the graphs and the traces).

## What you get

Everything the app does is written down in three ways, and one screen (Grafana) shows all three:

| Kind | What it answers | Tool (what it is) |
|---|---|---|
| **Logs** | *What happened, in order?* One JSON line per event, each with the request ID, the trace ID, the coaching (`organization_id`) and the person (`user_id`) when known | **Loki** (stores logs and lets you search them) |
| **Traces** | *Where did the time go, and where did it fail?* One request becomes a tree of steps: the web server, the API, each database statement, the background job it queued | **Tempo** (stores traces) |
| **Metrics** | *How is it doing right now?* Requests per second, errors, speed, waiting jobs, sign-in failures, imports, database connections | **Prometheus** (collects numbers every 15 seconds) |

**Grafana** is the screen that shows all three. **OpenTelemetry** is the open standard the app uses to send traces and
logs, and the **Collector** is the small post office in between that forwards them to Tempo and Loki.

## Turn it on (and off)

It is **off** by default, so everyday `docker compose up` stays light. It needs about 1.5 to 2 GB of memory while running.

1. Open the file `.env` in the project folder (create it from `.env.example` if you have none). It is never committed to Git.
2. Add these three lines (choose your own password):

   ```
   COMPOSE_PROFILES=observability
   OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
   GRAFANA_ADMIN_PASSWORD=choose-a-password-only-you-know
   ```

3. Start (or restart) the app:

   ```bash
   docker compose up -d
   ```

4. Open **http://localhost:3001** and sign in as user `admin` with your password.
   Grafana is reachable only from this PC (`127.0.0.1`); nothing else is published to the network.

To turn it off, delete (or put `#` in front of) the first two lines and run `docker compose up -d` again;
add `docker compose --profile observability down` once to stop the monitoring containers.
Stored data lives in Docker volumes and is kept 7 days (logs and traces) or 15 days (metrics).

## The screens

Under **Dashboards** (left menu) you find two:

- **Question Bank: overview**: traffic, errors, speed, background jobs, sign-ins, imports and the database, on one page.
  What to look at first: *Server errors (5xx)* should be 0%; *API and worker up* should be 2; *Age of the oldest ready job*
  should stay near 0 (if it grows, the worker is stuck or too slow).
- **Question Bank: follow one request**: paste a request ID and see every log line and the trace of that request.

## Trace a failing request, step by step

Say a teacher reports "something went wrong when I saved a question".

1. **Get the request ID.** An error response carries it twice: in the `X-Request-ID` header and in the JSON body
   (`error.request_id`, it starts with `req_` or `web_`). In the browser: press F12, open the **Network** tab, click the red
   request, look under *Response Headers*. (If you have no ID, use step 5 instead.)
2. **Open the dashboard** *Question Bank: follow one request* and paste the ID into **Request ID**.
   You see every log line of that request, from the web server, the API and the worker, oldest at the bottom.
   The `event` field says what happened (for example `request_completed`, `unhandled_error`, `job_failed`) and
   `route` says which endpoint (always the template, like `/api/v1/questions/{id}`, never the raw address).
3. **Open the trace.** Click a log line, then the link **Open trace** next to `trace_id`. (This works at once. The
   *Traces of this request* table on the dashboard needs about a minute before a brand-new trace appears in it.)
   You see the steps as a tree
   with their times. A red span is the step that failed; its `error.type` attribute names the kind of error.
   SQL steps show the statement with `%(placeholders)s`, never the values.
4. **Go back to the logs of the same trace.** In the trace view, click the logs icon on any step to see the log lines
   of that trace.
5. **No ID?** Open **Explore** (compass icon), choose **Loki**, and search for recent errors, for example:

   ```
   {service_name=~"qbank-.+"} | json | level="error"
   ```

   or one coaching's problems: `{service_name=~"qbank-.+"} | json | organization_id="<id>" | level=~"error|warning"`.

A background job continues the trace of the request that queued it, so a failed import or job shows up in the **same** trace.

## What is never recorded

Decided in ADR-0019 and proved by tests: passwords, session and CSRF tokens, activation or reset links, sign-in codes,
API keys, `Authorization` and `Cookie` headers, request and response bodies, uploaded file contents, and any question,
option, solution or other coaching content. Query strings are never logged. People appear as `user_id`, never as an
email, name or phone number. The client address appears only in `login_failed` and `rate_limited` events.
A safety net blanks forbidden fields and token-shaped text just before anything is written, but the rule for developers
is still: log identifiers, not content.

`organization_id` is on logs, traces and a few counters (imports and jobs), so one coaching's activity can be found; only you
(the platform operator) can open Grafana, never a coaching's staff.

## The numbers (metrics) and what they mean

| Metric | Meaning |
|---|---|
| `qbank_http_requests_total{method,route,status_class}` | requests answered; `5xx` = our errors |
| `qbank_http_request_duration_seconds` | how long requests took, per route |
| `qbank_db_pool_connections{state}` | database connections in use / idle |
| `qbank_login_attempts_total{method,outcome,reason}` | sign-ins by password, Google or link; why one failed |
| `qbank_rate_limited_total{scope}` | requests refused for coming too fast |
| `qbank_import_events_total{organization_id,event}` | syllabus imports per coaching: uploaded, apply_requested, rejected |
| `qbank_jobs_finished_total{job_type,outcome,organization_id}` | jobs finished: succeeded, retried, failed, lease_lost |
| `qbank_job_duration_seconds` | how long jobs took, per type |
| `qbank_jobs_queue_depth{job_type,state}` | jobs waiting (QUEUED) or running |
| `qbank_jobs_oldest_ready_age_seconds{job_type}` | how long the oldest ready job has waited |

Try your own questions in **Explore** with the **Prometheus** source, for example `sum(rate(qbank_http_requests_total[5m]))`.

## If something looks wrong

- **Grafana shows "No data" everywhere:** check `.env` has the three lines above, then `docker compose ps` lists
  `otel-collector`, `tempo`, `loki`, `prometheus`, `grafana`. Restart the app after changing `.env`: `docker compose up -d`.
- **Graphs work but logs and traces are empty:** the app needs `OTEL_EXPORTER_OTLP_ENDPOINT` (it is read at start-up, so restart
  the `api` and `worker` containers). Check the Collector with `docker compose logs otel-collector`.
- **Graphs are empty but logs work:** in **Explore** (Prometheus) run `up`; `0` for `qbank-api` or `qbank-worker` means Prometheus
  cannot reach the metrics page (port 9100 / 9101 inside the network; they are never published to your PC).
- **You forgot the Grafana password:** `GRAFANA_ADMIN_PASSWORD` in `.env` is used only the first time Grafana starts, so changing
  it later does nothing. Reset it without losing any data:

  ```bash
  docker compose exec grafana grafana cli admin reset-admin-password "your new password"
  ```

  and put the same password in `.env` so you remember it.
- **Never run `docker compose down -v`** to "start the monitoring fresh": `-v` deletes **every** volume of the project, including
  the database (`pgdata`) and uploaded pictures (`assetdata`). To clear only the monitoring data, stop the stack
  (`docker compose --profile observability down`) and remove just its volumes:
  `docker volume rm qbank_tempodata qbank_lokidata qbank_promdata qbank_grafanadata`.
- **It uses too much memory:** turn it off (above) when you are not debugging.

## Moving to the cloud later (M7)

The app only sends standard OpenTelemetry data to one address (`OTEL_EXPORTER_OTLP_ENDPOINT`) and publishes Prometheus
numbers; only `infra/observability/otel-collector.yaml` knows about Tempo and Loki. A cloud's own monitoring (or a managed
Grafana) replaces the containers without changing the application.
