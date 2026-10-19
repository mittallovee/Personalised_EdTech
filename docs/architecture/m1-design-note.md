# M1 Design Note — Foundation ("walking skeleton")

> Status: **Approved** (owner, 18 Oct 2026) · in progress · Milestone M1 of Phase 1 ([phase plan](../product/02-phase-plan.md))
> Requirements: A-01, A-03, N-01, N-05, N-07, N-08, N-13, N-14 · ADRs 0002–0007, 0010–0013

## 1. Goal

Build the thinnest end-to-end system that proves the architecture works: web → API → database → worker,
with tenant isolation, logging, tests and CI, and **no business features yet**. Every later milestone adds
features onto this skeleton without changing its foundations.

## 2. What you will be able to do at the end of M1

1. On your Windows PC: `docker compose up` → open `http://localhost:3000`.
2. Run one command to create the first **platform admin** (`qbank create-platform-admin`).
3. Log in with that email + password, see a home page showing "who am I" and system health; log out.
4. See CI run automatically on every pull request on GitHub.

## 3. Components

| Process | Tech | Port (local) | Responsibility in M1 |
|---|---|---|---|
| `postgres` | PostgreSQL 17 (supported by AWS RDS and Google Cloud SQL) | 5432 (internal only) | Data, RLS, job queue |
| `api` | FastAPI (Uvicorn) | 8000 | `/health/*`, auth (password + session), `/api/v1/me` |
| `worker` | same Python package, `python -m qbank.worker` | — | Runs background jobs (M1: a `noop` health job) |
| `web` | Next.js | 3000 | Login page, home page, app shell |
| `migrate` | one-off container | — | `alembic upgrade head` before api/worker start |

All bound to `localhost` only. Data in named Docker volumes (`pgdata`, `files`), so restarts keep data.

## 4. Repository skeleton created in M1

```text
compose.yaml · .env.example · Makefile · AGENTS.md · CLAUDE.md · README.md
api/openapi.json
services/api/
  pyproject.toml · uv.lock · alembic.ini · .importlinter
  src/qbank/
    main.py · worker.py · cli.py
    core/  config.py db.py tenancy.py auth.py security.py errors.py logging.py ids.py jobs.py storage.py
    modules/
      identity/       (users, password login, sessions, /me)
      organizations/  (organizations, memberships; platform roles)
      audit/          (audit_events)
      health/         (/health/live, /health/ready)
  migrations/versions/0001_foundation.py
  tests/ unit/ integration/ api/ conftest.py
apps/web/
  package.json · next.config · tsconfig (strict) · eslint/prettier config
  src/app/(auth)/login · src/app/(app)/home · src/lib/api.ts
packages/api-client/   (generated from api/openapi.json)
infra/docker/          api.Dockerfile · web.Dockerfile
.github/workflows/ci.yml
```

## 5. Database (migrations `0001_foundation` and `0002_identity`)

Two DB roles: `qbank_owner` (owns tables, runs migrations) and `qbank_app` (runtime: no ownership, no
superuser, no `BYPASSRLS`). `qbank_app` is created outside migrations (locally by the `db-init`
compose service running `infra/db/ensure-app-role.sh` on every start, so existing volumes work too; in the
cloud by infrastructure code), so no password lives in a migration.

Split (decided during PR 2 to keep PRs small): **0001** = organizations, users, memberships, audit_events
(PR 2). **0002** = password_credentials, platform_roles, sessions (PR 3). The `jobs` table comes with PR 4.

| Table | Key columns | RLS |
|---|---|---|
| `organizations` | `id` (UUIDv7), `display_name`, `status` (ACTIVE/SUSPENDED), `timezone` (default Asia/Kolkata), `created_at`, `updated_at` | Visible to platform context, or to members where `id = app.org_id` |
| `users` | `id`, `display_name`, `status`, `created_at` | Not tenant-owned (a user can exist before membership); access only via service layer |
| `password_credentials` | `user_id` PK, `email` (unique, lower-case), `password_hash` (Argon2id), `failed_attempts`, `locked_until` | Service layer only |
| `platform_roles` | `user_id`, `role` (PLATFORM_ADMIN), `granted_at` | Service layer only |
| `memberships` | `id`, `organization_id`, `user_id`, `role` (OWNER/ADMIN/FACULTY), `status`; unique active membership per user | **Tenant RLS** |
| `sessions` | `id`, `user_id`, `token_hash` (SHA-256), `csrf_token_hash`, `acting_organization_id` NULL, `created_at`, `last_seen_at`, `idle_expires_at`, `absolute_expires_at`, `revoked_at` | Service layer only |
| `audit_events` | `id`, `organization_id` NULL, `actor_user_id`, `actor_is_platform`, `action`, `entity_type`, `entity_id`, `before`, `after` (JSONB), `request_id`, `created_at` | **Tenant RLS** (platform-level events have NULL org, visible in platform context) |
| job tables | created by the queue library + our `jobs` table (`id`, `organization_id`, `type`, `state`, `attempts`, `request_id`, timestamps) | **Tenant RLS** |

**Tenant context mechanics** (`core/tenancy.py`):
```text
request → authenticate → Principal(user_id, org_id | None, is_platform, acting_org_id | None)
        → begin transaction
        → SET LOCAL app.org_id = <org or acting org>, SET LOCAL app.is_platform = <true|false>
        → service code → commit
```
Policies use `current_setting('app.org_id', true)`, so a missing setting returns no rows (**fail closed**).
The web app never sends an organization ID.

## 6. API endpoints in M1

| Method & path | Purpose | Auth |
|---|---|---|
| `GET /health/live` | Process is up | none |
| `GET /health/ready` | DB reachable + migrations at head | none |
| `POST /api/v1/auth/login` | Email + password → sets `qb_session` cookie + returns CSRF token | none (rate-limited) |
| `POST /api/v1/auth/logout` | Revokes current session | session + CSRF |
| `GET /api/v1/me` | Current user, roles, organization (if any), acting organization | session |

Error envelope, request IDs and pagination helpers are implemented now (even if few endpoints use them yet).
Login failures return one generic message (no "email not found" leaks); progressive delay after 5 failures.

## 7. CLI

```bash
docker compose run --rm migrate qbank create-platform-admin --email you@example.com
# prompts for name + password (min 12 chars), refuses if a platform admin with that email exists
```

Runs in the `migrate` service because creating a platform admin needs the table-owner connection;
the runtime role is deliberately unable to create accounts or read password hashes.

**Login data access (added in PR 3):** the runtime role has no privileges on `password_credentials`.
Login uses four `SECURITY DEFINER` functions (`auth_find_login`, `auth_register_login_failure`,
`auth_register_login_success`, `auth_find_session`) executable only by `qbank_app`. Sessions and
platform roles are visible to the runtime role only for the signed-in user.

## 8. Web (M1)

- Login page (email, password, errors shown from the error envelope).
- App shell: top bar (user name, logout), side navigation placeholders for later modules.
- Home: "Signed in as …, platform admin", API health status.
- Uses the generated API client only. Session cookie is handled by the browser; CSRF token sent on mutations.

## 9. Background jobs (M1)

`core/jobs.py` exposes `enqueue(session, job_type, payload, *, context, idempotency_key)`, a `JobRegistry` and a
`Worker` (`python -m qbank.worker`, the `worker` compose service). M1 ships a `health.ping` job. Tests prove:
enqueue in the same transaction as a data change (rollback = no job), each job runs once inside its own
coaching, the handler's writes and "job done" commit together, retries with growing backoff (2 s, 10 s, 60 s…),
permanent errors and unknown job types are not retried, an idempotency key creates one job per coaching, a
running job cannot be claimed twice, and a crashed worker's job is recovered while its late result is discarded.

Jobs live in the `jobs` table (migration 0003). The runtime role may enqueue and read its own coaching's jobs;
claiming/completing/failing across coachings goes through `jobs_claim`, `jobs_complete`, `jobs_fail`
(SECURITY DEFINER, executable only by `qbank_app`). See ADR-0007's implementation note.

**Codes (T11):** `core/codes.py` generates 8-character Crockford Base32 codes, normalises typed input
(lower case, O→0, I/L→1, hyphens/spaces ignored) and `reserve_code` records each code in `public_codes`
(global primary key, never changed or reused), retrying on collision.

## 10. Observability (M1)

- structlog JSON logs for API and worker; `X-Request-ID` middleware; request ID passed into jobs.
- OpenTelemetry instrumentation wired, exporting only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
- Sentry initialised only when `SENTRY_DSN` is set.

## 11. CI (`.github/workflows/ci.yml`)

Runs on every PR and push to `main`: backend lint/format/types/import-boundaries, pytest (unit + integration +
API) against a PostgreSQL service container, migration up/down/up, OpenAPI export equals committed file;
web lint/typecheck/test/build; secret scan; dependency audit. (Details: [standards §10](../engineering/standards.md).)

## 12. Tests that prove M1 (exit criteria)

| # | Test | Type |
|---|---|---|
| T1 | Two coachings A and B with memberships: in context A, B's memberships/audit rows/jobs are invisible and cannot be inserted/updated | integration |
| T2 | No tenant context set → zero rows from tenant tables | integration |
| T3 | Runtime role `qbank_app` cannot disable RLS, cannot alter tables, is not owner | integration |
| T4 | Insert with `organization_id` ≠ context is rejected (`WITH CHECK`) | integration |
| T5 | Login success sets an HttpOnly cookie; wrong password → generic 401; locked after repeated failures | api |
| T6 | Logout revokes session; old cookie → 401; mutation without CSRF header → 403 | api |
| T7 | `/me` returns principal; unauthenticated → 401 with error envelope and request ID | api |
| T8 | Migrations: upgrade head → downgrade base → upgrade head on empty DB | integration |
| T9 | Job: enqueued in a rolled-back transaction never runs; committed job runs once; retry with backoff; duplicate idempotency key runs once | integration |
| T10 | Restart `docker compose` → data still present, health ready | manual check (documented) |
| T11 | Code generator: 8 chars, Crockford alphabet, normalisation of O/I/L, collision retry | unit |
| T12 | OpenAPI committed file matches generated | CI |

## 13. Out of scope for M1

Google login, invitations, coaching creation UI, grants (M2); any question/taxonomy feature (M3+); AI (M5);
uploads (M6); cloud deployment (M7).

## 14. Work plan (pull requests)

| PR | Content | Status |
|---|---|---|
| 1 | Repo skeleton, tooling configs, compose, Dockerfiles, CI with lint/format only | Merged (#2) |
| 2 | Backend core: config, logging, errors, request ID, health endpoints, DB session, migration 0001, RLS + tests T1–T4, T8 | Merged (#3) |
| 3 | Identity: migration 0002, password hashing, sessions, login/logout/me, CLI, tests T5–T7 | Merged (#4) |
| 4 | Jobs core + worker + T9; ID/code generator + T11 (migration 0003) | In review |
| 5 | Web: app shell, login, home, generated client, OpenAPI check T12; Origin allow-list on unsafe API requests (owner decision, 19 Oct) | |
| 6 | README run instructions, restart check T10, M1 demo notes | |

## 15. Decisions for the owner

1. Approve this design note (or request changes).
2. GitHub settings only you can change: protect `main` (require PR, CI green, your approval). I'll give
   step-by-step instructions when PR 1 is ready.
3. Install on your PC before PR 6 demo: **Docker Desktop** with the **WSL2** backend, and **Git**.
