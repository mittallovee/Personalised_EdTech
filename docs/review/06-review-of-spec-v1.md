# 06 — Review of spec-v1 (Consolidated Requirements Package, 18 Oct 2026)

> Reviewed: all 52 current documents in [`docs/spec-v1/`](../spec-v1/docs/README.md) (plus a look at the original handover zip).
> Severity: 🔴 resolve before coding starts · 🟠 resolve before that slice · 🟢 improvement.

## 1. Verdict

spec-v1 is a **big step up** from spec-v0. The product requirements are now clear, specific and mostly
decided. Most of the questions in [04-open-questions](./04-open-questions.md) are answered, and the domain
rules are at the level of detail engineers can build from.

It is **ready for coding the first slice**, provided a few engineering items are added first (section 4).
Those items are exactly the two concerns you started with:

1. *"A backend that many different apps can call"* — the API is designed for **one browser web app only**.
2. *"Code that humans can manage, not vibe coded"* — there are **no engineering-practice rules** (repo
   structure, linting, CI, code review, logging/monitoring). The plan hands implementation to an AI coding
   agent (Codex), which makes these rules more important, not less.

Both are cheap to fix now and expensive to retrofit later.

## 2. What's very good (industry-grade already)

| Practice | Where | Why it matters |
|---|---|---|
| **Traceability matrix**: requirements R-01–R-39 → decisions D-01–D-23 → acceptance tests AT-01–AT-48 | REQUIREMENTS_TRACEABILITY, DECISION_REGISTER, ACCEPTANCE_TEST_PLAN | This is how regulated/large companies prove every requirement is built and tested |
| **Confirmed vs proposed** labelling (D-xx product decisions vs P-xx engineering proposals) | All docs | Nobody mistakes an engineer's guess for a business rule |
| **Revision-bound approval**: QC/approval/publish point to an exact revision hash; any edit invalidates them | QUESTION_LIFECYCLE_AND_QC, P-05/P-06 | Stops the classic bug "approved version A, published edited version B" |
| **Optimistic concurrency** (ETag / If-Match → 412 on stale write) | API_CONTRACTS_DRAFT, P-12 | Two reviewers can't silently overwrite each other |
| **Idempotency keys** bound to request hash | P-13 | Retries never create duplicate questions |
| **Defence-in-depth tenancy**: Postgres **RLS**, non-owner DB role, composite tenant foreign keys | SECURITY, DATABASE_SCHEMA | Even a coding mistake in a query can't leak another coaching's data |
| **Durable jobs** in Postgres + **outbox**, Redis only as broker | BACKGROUND_JOBS, P-20 | A PC restart or queue loss doesn't lose work |
| **Exact answer rules** with valid/invalid fixtures for all 9 formats; decimals as strings, no float rounding | QUESTION_TYPES, QUESTION_SCHEMA_EXAMPLES | Validators can be written test-first from these examples |
| **AI cost controls**: reservations before dispatch, actual/estimated/unknown cost, "unknown ≠ zero" | AI_USAGE_AND_COST, P-27/P-28 | Prevents surprise AI bills |
| Translations and variants are **separate masters** with source-version links | LANGUAGE_SUPPORT, D-15 | Resolves spec-v0 issue I-2 (answer stored per language) |
| **Thin first slice** with clear exit evidence | IMPLEMENTATION_ROADMAP | Matches the "walking skeleton" approach from [03](./03-recommended-approach.md) |

## 3. Your earlier open questions — status

| # | Question | Answer in spec-v1 | Status |
|---|---|---|---|
| Q1 | Who is it for? | One coaching first; multi-coaching SaaS architecture; platform admin creates coachings | ✅ |
| Q2 | Shared master bank? | No. Each coaching private; platform admin may make a one-time independent copy | ✅ |
| Q3 | Existing data/systems | Existing PDF/Word/image sources (text + scanned); samples later | ✅ (no existing software to integrate) |
| Q4 | Which apps first | Release one = faculty/admin web only. Tests, student app, courses, live classes later | ✅ |
| Q5 | Live-exam scale | Deferred to later phase | ⏳ deferred — see 🔴 A1 |
| Q6 | Student identity | Deferred. Faculty: Google / email-password / mobile OTP linked to one account | ⏳ partly |
| Q7 | Subjects/languages | JEE/NEET Physics first; 7 languages (en, hi, gu, bn, mr, te, ta) | ✅ |
| Q8 | Review workflow | Separate QC / approve / publish grants; self-approval allowed with grants; shared queue | ✅ |
| Q9 | Team | Not stated. Development on your Windows PC; implementation handed to Codex | ❓ still open |
| Q10 | Hosting/budget | Local PC for development; production hosting & budget deferred | ⏳ deferred |
| Q11 | Tech stack | Not user-selected; proposed Next.js + FastAPI + PostgreSQL + Celery/Redis (P-01) | ❓ needs your OK |
| Q12 | Timeline | Not stated | ❓ still open |
| Q13 | Uptime/data loss | Deferred (backup proposal P-34 exists) | ⏳ deferred, fine for local |
| Q14 | External API consumers | Not addressed | ❓ see 🔴 A1 |
| Q15 | Payments | Later phase | ✅ |

### Stack: I now recommend accepting P-01 (revising my earlier suggestion)
In [03](./03-recommended-approach.md) I suggested a TypeScript/NestJS backend. Given the requirements that are
now confirmed, **FastAPI (Python) is the better choice**:
- The hardest parts (PDF/DOCX parsing, OCR, handwriting, AI orchestration) have the best tools in Python,
  so the API and the workers share one language.
- FastAPI **generates an OpenAPI contract automatically** from typed models, which is exactly what multiple
  frontends need.
- Next.js/TypeScript for the web UI stays as proposed.

## 4. Gaps to close before coding

### 🔴 A1 — Design the API for many clients now (build later)
**Current state:** opaque session **cookies + CSRF** (P-10), "web and API share a common entry point", no
OpenAPI file, no token authentication, no rate-limiting policy per client, no versioning/deprecation policy.
Cookies work well for the faculty web app, but a native student app, a live-exam app or a partner system
cannot use them properly.

**Recommendation (one ADR, no extra features in release one):**
- Keep cookie sessions for the faculty web app (correct choice for browsers).
- State now that **all business logic sits behind the versioned `/api/v1` JSON API** and the web app uses
  only that API — no hidden server-side shortcuts in Next.js.
- Make the auth layer pluggable: requests resolve to the same "authenticated principal + coaching + grants"
  whether they come from a cookie session or (later) an **OAuth2/OIDC bearer token** (mobile apps use the
  **PKCE** flow). Business modules must never read cookies directly.
- **Export the OpenAPI spec into the repo** (`api/openapi.json`) on every change, review diffs in PRs and
  fail CI on **breaking changes**. Generate the TypeScript client for the web app from it.
- Write a short **API style guide** (naming, errors — already good, pagination — already good, versioning and
  deprecation rules).

### 🔴 A2 — Engineering standards ("not vibe coded" guardrails)
No document covers how code is written, checked or reviewed. The original handover had a repo layout and an
"audit/observability" module, but the consolidated pack dropped both. Add one `ENGINEERING_STANDARDS.md` and an
`AGENTS.md` (instructions file the AI coding agent reads automatically) before slice 1:

| Area | Proposed default |
|---|---|
| Repo layout | Monorepo: `apps/web` (Next.js), `services/api` (FastAPI, `modules/<name>/` per bounded context), `services/worker`, `migrations/`, `docs/`, `infra/` |
| Module boundaries | Each module exposes a small public interface; others may not import its internals or tables. Enforce with **import-linter** (Python) and ESLint boundaries (TS) in CI |
| Code quality | Python: **ruff** (lint + format), **mypy/pyright** strict on domain code. TS: ESLint, Prettier, `tsc --strict` |
| Tests | **pytest** unit + integration against real PostgreSQL (the pack already says SQLite/mocks can't prove RLS), **Playwright** for UI flows; the 48 AT scenarios become real tests slice by slice |
| CI (GitHub Actions) | On every PR: lint → typecheck → unit → integration (Postgres container) → OpenAPI diff → migration check → build |
| Review | Protected `main`, PR required, CI green, a human reads every PR (especially AI-written ones), small PRs, PR template with security/tenant/migration checklist |
| Decisions | Convert D-xx/P-xx into one-file **ADRs** as each is implemented |
| AI agent rules | `AGENTS.md`: read the spec first, one slice/story per PR, write tests with the code, never weaken RLS/validators to make tests pass, report only tests actually run |

### 🔴 A3 — Observability (logging, metrics, tracing)
Not covered anywhere (zero hits for logging/metrics/tracing). The pack has `correlation_id` in errors and an
audit table, but **operational** visibility is also needed: structured JSON logs with request/job/correlation
IDs, job queue depth/age metrics, provider latency/error metrics, error tracking (e.g. Sentry), and
**OpenTelemetry** so traces follow a request from browser → API → worker → AI provider. Cheap to add in slice 1,
painful to retrofit.

### 🟠 B1 — Search technology is unspecified
`GET /questions` has filters but **no free-text search parameter**, and duplicate detection says "bounded
semantic retrieval" without choosing how. Recommendation (one ADR): PostgreSQL **full-text** + **pg_trgm**
(fuzzy) + **pgvector** (embeddings for semantic duplicates) inside the same database, measured on a
lakh-scale fixture before considering OpenSearch. Note: Postgres has no stemming for Indian languages, so
trigram + embeddings carry more weight for hi/gu/bn/mr/te/ta.

### 🟠 B2 — Answer domains: check against real PYQs before freezing
Confirmed rules: integer 0–999, numerical 0.00–999.00, **no negatives**, SCQ/multi-correct **exactly 4
options**. These fit most JEE/NEET Physics, but before coding the validators, check your PYQ corpus for
answers that are **negative** or **above 999** (both may occur in JEE numerical questions). Recommendation:
keep the confirmed values as defaults but store them as **configuration per question type/exam**, not
hard-coded constants, so a later exam or subject doesn't need a code change.

### 🟠 B3 — Translation drift
A translation is an independent master linked to an exact source version. If the English answer is later
corrected, nothing tells anyone the Hindi translation still has the old answer. Add a derived **"source has a
newer published version"** flag on `translation-of` (and `variant-of`) relations, shown in the UI and the
review queue. It's cheap now, and bilingual papers in the later test builder will need it.

### 🟠 B4 — Taxonomy sprawl from AI
AI may create concepts and prerequisites that can be used immediately. At lakh scale this can produce
near-duplicates ("Newton's second law" / "Newton's 2nd law of motion"). Alias matching and admin merge exist;
add a **pending-review count/age metric** and alias matching before creation as an explicit acceptance test.

### 🟢 C1 — Release-one size vs team size
Release one is large: 9 formats, 7 languages, handwriting OCR, adaptive layout learning, 4 AI providers,
budget reservations, a knowledge graph and cross-coaching copy. The 8-slice roadmap is good. Two suggestions
that don't drop any confirmed scope:
- **Let faculty use it after slice 3** (manual bank + QC + publish + search) instead of waiting for slice 8.
  Real use finds problems early.
- Build **slice 7 (cross-coaching copy) when a second coaching actually exists**. It's the most complex
  feature and gives no value while there is only one coaching.

### 🟢 C2 — Readability of the documents
The content is strong, but the writing is very compressed and every document repeats "planned / not run /
not verified" disclaimers. A new engineer (or you, in six months) will find it hard going. Suggestions:
keep the status disclaimers in **one** status page (DOCUMENTATION_READINESS), add a **glossary** (spec-v1 has
none — [05-industry-vocabulary](./05-industry-vocabulary.md) can seed it), and add 2–3 **diagrams**
(context diagram, question lifecycle state diagram, ingestion flow).

## 5. Remaining questions for you (only 5)

1. **Who will write and review the code?** You + Codex only, or is there at least one human developer who
   will read PRs? This decides how strict the CI gates must be.
2. **Accept stack P-01** (Next.js + FastAPI + PostgreSQL + SQLAlchemy/Alembic + Celery/Redis, Docker/WSL2 on
   your Windows PC)? I recommend yes.
3. **Confirm "API-first for future apps"** (A1): cookie sessions now, token auth added later without
   changing business code, OpenAPI file in the repo. Yes/no?
4. **Answer domains** (B2): can you check a few PYQ papers for negative answers or answers above 999? And
   should the limits be configurable per exam?
5. **Target date** for faculty to start using slice 3 (manual bank + QC + publish + search)?

## 6. Suggested next step

Once you answer, I can write, in this repo: `ENGINEERING_STANDARDS.md`, `AGENTS.md`, `API_STYLE_GUIDE.md`,
and ADRs for stack, API/auth for multiple clients, observability and search. That's the missing engineering
layer. After you review those, slice 1 (local foundation) can start.

## Technical words used in this review

- **Traceability matrix** — table linking each requirement to the decision and test that covers it.
- **RLS (Row Level Security)** — PostgreSQL feature that filters rows per tenant inside the database itself.
- **ETag / If-Match / optimistic concurrency** — each record carries a version tag; an update must send the
  tag it read; if someone changed it meanwhile, the update is rejected (HTTP 412) instead of overwriting.
- **Idempotency key** — a client-chosen ID that makes retrying a request safe.
- **Outbox pattern** — events saved in the same DB transaction as the data, then sent, so none are lost.
- **Bearer token / OAuth2 / OIDC / PKCE** — how mobile and partner apps log in: they get a signed access
  token and send it with each request; PKCE is the secure variant for mobile apps.
- **OpenAPI / breaking change** — the machine-readable API contract; a breaking change makes existing
  clients fail.
- **import-linter / module boundaries** — a tool that fails the build when one module reaches into another's
  internals.
- **Observability / OpenTelemetry** — logs, metrics and traces that show what the running system is doing;
  OpenTelemetry is the standard way to collect them.
- **AGENTS.md** — a file in the repo that AI coding agents read for project rules.
- **YAGNI** ("You Aren't Gonna Need It") — don't build something until there's a real need (C1).
