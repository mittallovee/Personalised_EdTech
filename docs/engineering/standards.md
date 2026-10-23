# Engineering Standards

> Status: **Draft for owner review** · Applies to every change, whether written by a human, Claude Code or Codex.
> Decisions behind these rules: [`docs/architecture/adr/`](../architecture/adr/).

## 1. Principles

1. **Readable over clever.** A new engineer should understand a module in a day.
2. **The spec is the source of truth.** Every change traces to a requirement ID in
   [`docs/product/01-requirements.md`](../product/01-requirements.md) or an ADR.
3. **Rules are enforced by tools, not memory.** If a rule matters, CI checks it.
4. **Small, reviewable steps.** Small pull requests, each one green and deployable.
5. **Security and tenant isolation are never traded for speed.**
6. **Report honestly.** Only claim tests that actually ran; say what was not verified.

## 2. Repository layout (monorepo)

```text
/
├── AGENTS.md                 rules for AI coding agents (Claude Code, Codex)
├── CLAUDE.md                 imports AGENTS.md + Claude-specific notes
├── README.md                 what this is, how to run it
├── compose.yaml              local stack: postgres, api, worker, web
├── .env.example              every config variable, no real secrets
├── api/
│   └── openapi.json          the API contract (generated, committed, diff-checked in CI)
├── services/
│   └── api/                  Python backend (one package, two processes: API + worker)
│       ├── pyproject.toml    uv-managed, lockfile committed
│       ├── src/qbank/
│       │   ├── main.py       FastAPI app factory
│       │   ├── worker.py     background worker entry point
│       │   ├── cli.py        admin commands (e.g. create-platform-admin)
│       │   ├── core/         cross-cutting: config, db, tenancy, auth, errors, logging, ids, storage
│       │   └── modules/      one folder per bounded context (see §3)
│       ├── migrations/       Alembic
│       └── tests/            unit/, integration/, api/
├── apps/
│   ├── web/                  Next.js + TypeScript faculty/admin app
│   └── e2e/                  browser tests (Playwright) against the running stack
├── packages/
│   ├── api-client/           TypeScript client generated from api/openapi.json
│   └── content-renderer/     shared question renderer (KaTeX), reused by future student apps
├── infra/                    Dockerfiles, DB role setup, operational scripts; later Terraform for cloud
├── docs/                     product, architecture, engineering, operations
└── .github/                  CI workflows, PR template, CODEOWNERS
```

## 3. Backend module structure

Each bounded context is a folder under `src/qbank/modules/` (e.g. `identity`, `organizations`, `taxonomy`,
`questions`, `review`, `ingestion`, `ai`, `prompts`, `search`, `notifications`, `audit`).

```text
modules/questions/
├── __init__.py
├── public.py        ← the ONLY thing other modules may import (service functions + DTOs)
├── api.py           FastAPI router: HTTP ↔ schemas, no business logic
├── schemas.py       Pydantic request/response models (become the OpenAPI contract)
├── service.py       use cases: authorization, transactions, orchestration
├── domain/          pure rules (validators, state machine) — no DB, no HTTP, no I/O
├── repository.py    SQLAlchemy queries for this module's tables only
├── models.py        SQLAlchemy table models (owned by this module)
└── jobs.py          background job handlers for this module (if any)
```

**Dependency rules** (enforced by `import-linter` in CI):
- `api → service → domain` and `service → repository → models`. Never the reverse.
- `domain/` imports nothing from FastAPI, SQLAlchemy or other modules.
- A module imports another module **only through its `public.py`**, and never touches another module's tables.
- `core/` must not import from `modules/`.

## 4. Coding rules

### Python (backend)
- Python version and dependencies pinned in `pyproject.toml` + `uv.lock`.
- **ruff** for lint + format (no style debates), **mypy --strict** for `core/` and `modules/*/domain/`; typed everywhere else.
- Pydantic models at every boundary (HTTP, jobs, AI outputs). Never pass raw dicts across modules.
- SQL only through SQLAlchemy with bound parameters. **No string-built SQL.**
- Money/decimals: `Decimal`, never `float`. Numerical answers are decimal strings (D-02).
- Time: timezone-aware UTC everywhere; convert to the coaching's timezone only for display/budget periods.
- Errors: raise typed domain exceptions (`NotFound`, `PermissionDenied`, `Conflict`, `ValidationFailed`…);
  one handler maps them to the API error envelope. No bare `except:`.
- Functions do one thing; files > ~400 lines or functions > ~50 lines need a reason.
- Comments explain *why*, not *what*. Public service functions have docstrings.

### TypeScript (web)
- `strict: true`, ESLint + Prettier, no `any` (use `unknown` + narrowing).
- Server data only through the generated `@qbank/api-client` and TanStack Query. No hand-written fetch URLs.
- Components small and typed; pages compose feature components (`features/<area>/`).
- **Never** render question content as raw HTML. Use `@qbank/content-renderer` only.
- UI permission checks are cosmetic. The API is the authority.

## 5. Security rules (non-negotiable)

1. Every endpoint resolves the **principal** and **tenant context** server-side; never trust an
   `organization_id` from the client.
2. Every protected service function starts with an explicit permission check (`require(principal, Grant.PUBLISH)`).
3. Every tenant-owned table has `organization_id`, a row-level-security policy and tests (ADR-0005).
4. The runtime database role is not the table owner and cannot bypass RLS.
5. No secrets in code, logs, test fixtures, error messages, prompts or the browser. Use environment
   variables / secret store. A secret scanner runs in CI.
6. Validate uploads by content (magic bytes), size and type; process documents in isolated workers.
7. Treat all document and AI-generated text as **untrusted data** (prompt injection, XSS).
8. Passwords: Argon2id. Sessions: random tokens stored hashed. Cookies: HttpOnly, Secure, SameSite.
9. Audit every state change that matters (who, what, when, before/after, request ID).

## 6. Database & migrations

- Alembic migrations, reviewed like code; one logical change per migration; descriptive names.
- **Expand → migrate → contract** for changes to existing data; never drop/rename in one step on real data.
- Every migration must `upgrade` and `downgrade` cleanly on an empty DB (CI checks). Irreversible data
  migrations document their compensating action.
- Foreign keys always; composite `(organization_id, id)` keys for tenant-owned parents.
- Indexes justified by a query (note it in the migration).
- Destructive dev commands refuse to run unless `APP_ENV=local` and the DB name ends in `_dev` or `_test`.

## 7. Testing strategy

| Layer | Tool | What | Where |
|---|---|---|---|
| Unit | pytest | Domain rules: validators for all 9 formats, state machine, permission decisions, code generator, budget maths | `tests/unit` |
| Integration | pytest + real PostgreSQL | Repositories, RLS isolation, transactions, migrations, jobs | `tests/integration` |
| API | pytest + httpx | Endpoints: auth, status codes, error envelope, ETag/idempotency, permission denials | `tests/api` |
| Contract | OpenAPI diff | No unintended breaking API change | CI |
| Web unit | Vitest + Testing Library | Components, form logic | `apps/web` |
| End-to-end (browser) | Playwright + Chromium | What a person does in the browser, against the whole stack (`docker compose`): sign-in, account activation now; user journeys J1–J7 as they are built | `apps/e2e` |
| Security | ruff `S` (bandit), pip-audit, pnpm audit, gitleaks | Risky Python code; libraries with known vulnerabilities; committed secrets | CI (`ci.yml`, `security.yml`, weekly too) |
| AI evaluation | pytest-based eval harness | Extraction/verification/translation quality on the golden set | `tests/eval` (not in normal CI; run on demand) |

When each runs:
1. **While writing code** (developer or agent, on their machine): unit, API and integration tests for the
   code being changed; the browser tests when a screen changes.
2. **On every pull request** (CI, automatically): everything in §10, including the browser tests and the
   security scans; Codex reviews the diff. A red check blocks the merge.
3. **After merging, at the end of a milestone** (the owner, by hand): the milestone demo script in
   `docs/operations/` on their own PC, checking it does what the requirements say.
4. **Weekly** (CI schedule): the dependency audits again, because new advisories appear for unchanged code.

Rules:
- **Every bug fix starts with a failing test.**
- A new or changed screen gets a browser test for its main path and its most likely mistake.
- Tenant isolation tests exist for every tenant-owned table (two-coaching fixture).
- No mocks for PostgreSQL behaviour (RLS, constraints). Mock only external services (AI providers, Google OAuth).
- Coverage: domain code ≥ 90%; overall is a signal, not a target.
- Tests use synthetic data only, never real coaching content or keys.

## 8. Observability

- **Structured JSON logs** (structlog) with `request_id`, `job_id`, `organization_id`, `user_id`, `operation`,
  `duration_ms`, `outcome`. Never log secrets or full question content.
- Every HTTP response carries `X-Request-ID`; jobs inherit the request ID that created them.
- **OpenTelemetry** traces for API, DB and outgoing AI calls; metrics for request rate/latency/errors,
  job queue depth/age, AI tokens/cost/errors.
- Errors to Sentry when `SENTRY_DSN` is set.
- `/health/live` (process up) and `/health/ready` (DB reachable, migrations current).

## 9. Git & pull requests

- `main` is protected: PR required, CI green, owner approval. No direct pushes, no force-pushes.
- Short-lived branches: `feat/<area>-<short>`, `fix/…`, `docs/…`, `chore/…` (AI sessions may use their assigned branch).
- **Conventional commits**: `feat(questions): add numerical answer validator`.
- PR size: aim < 400 changed lines (generated files excluded). Split otherwise.
- PR description uses the template: what/why, requirement IDs, how tested (actual commands + results),
  screenshots for UI, risks, checklist.
- Review: Claude Code self-reviews the diff; Codex may review; **the owner approves and merges**.

## 10. CI pipeline (GitHub Actions, every PR)

```text
backend:  ruff check · ruff format --check · mypy · import-linter
          pytest unit + integration + api (PostgreSQL service container)
          alembic upgrade head → downgrade base → upgrade head (empty DB)
          export OpenAPI → must equal committed api/openapi.json · oasdiff breaking-change check
web:      pnpm lint · typecheck · vitest · build · api-client regenerated == committed
e2e:      docker compose up --build → Playwright (Chromium) browser tests; report kept on failure
security: secret scan (gitleaks) · ruff S rules (in backend) · dependency audit (pip-audit on uv.lock,
          pnpm audit --prod), also weekly · Semgrep code scan: our rules in .semgrep/ (tests included)
          plus community packs. CodeQL needs a paid plan for private repos: not used.
updates:  Dependabot opens one pull request a week per ecosystem (Python, web, GitHub Actions, Docker
          images) in .github/dependabot.yml; patch and minor updates are grouped, a major update stands
          alone. Such a PR is reviewed and merged like any other: CI must be green, and a major update
          needs the owner's decision.
```

### Semgrep findings

A finding fails the build. Fix the code. If it is a false alarm, silence that one line with a comment
that names the rule and gives the reason, for example
`# nosemgrep: qbank-no-float-column -- mirrors a vendor field we only read`; the reason is reviewed like
code. Never switch a rule off to get green. New project rules go in `.semgrep/rules/` with a test case
for both a line that must be flagged and one that must not (`.semgrep/tests/`); run
`uvx --from semgrep semgrep --test --config .semgrep/rules .semgrep/tests`.

## 11. Definition of Done (per story / PR)

- [ ] Requirement IDs referenced; acceptance criteria met.
- [ ] Tests added/updated and **actually run**; CI green.
- [ ] Permissions and tenant isolation tested for new endpoints/tables.
- [ ] Audit events for significant state changes.
- [ ] Migration safe and reversible (or compensating action documented).
- [ ] Logs/metrics for new critical paths.
- [ ] OpenAPI + generated client updated if the API changed.
- [ ] Docs updated (requirements status, ADR if a decision was made, README if setup changed).
- [ ] No secrets, no TODOs without an issue link.

## 12. Configuration

- All settings via environment variables, parsed by `pydantic-settings` in `core/config.py`; app refuses to
  start if a required value is missing.
- `.env.example` lists every variable with a safe example. Real `.env` files are git-ignored.
- `APP_ENV` ∈ `local | test | staging | production`; production refuses development-only settings
  (e.g. insecure cookies).
