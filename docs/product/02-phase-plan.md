# Phase Plan

> Status: **Draft for owner review**. Requirement IDs refer to [01-requirements](./01-requirements.md).

## 1. Words used here

- **Phase**: a major release that gives users a new capability (e.g. Phase 3 = tests and papers). Each phase
  starts with a short discovery/design step for its own details.
- **Milestone** (also called a **slice**): a thin, complete piece of a phase, built end to end (database →
  API → screen → tests), deployed and demoed. Slices keep progress visible and reduce risk; you can see and
  use something real every 1–3 weeks.
- **Exit criteria**: the checks that must pass before a milestone/phase counts as done.
- **"Slice 3"** in the spec-v1 roadmap meant "manual question bank with review and publishing". In our plan
  that is milestones **M3 + M4**, the point where faculty can start entering real questions.

## 2. Phases at a glance

| Phase | Name | What users get |
|---|---|---|
| **P1** | **Question Bank Core** | Faculty create/import questions, AI helps (tag, translate, solve, check), review → publish, search; admin console; prompt library |
| P2 | Ingestion at scale & content intelligence | Paper/key/solution pairing, handwriting tuning, adaptive layouts (cheaper AI), semantic duplicates, knowledge graph, variants, diagrams, OTP login, bulk tools, storage dashboard, coaching copy |
| P3 | Tests & papers | Test builder, blueprints, marking schemes, PDF/Word paper export with answer key/solutions |
| P4 | Students & practice | Student accounts (OTP), batches/enrollment, consent (DPDP), student web + mobile app, practice & assignments, payments |
| P5 | Online tests & live exams | CBT engine: scheduling, server timer, autosave, shuffling, results, ranks, answer-key challenges |
| P6 | Learning analytics | Timing, concept mastery, difficulty calibration from real data, recommendations |
| P7 | Courses & classes | Courses, live classes, recorded sessions |
| P8 | Personalized AI teaching | Level-aware AI explanations and concept videos |

Confirmed (18 Oct): **P2 follows P1**. The order of P3–P8 can change; we re-plan after each phase with real usage data.

## 3. Phase 1 — Question Bank Core (in detail)

**Goal:** a coaching can put its existing and new Physics questions into a clean, reviewed, searchable bank,
with AI doing the heavy lifting and humans in control.

| Milestone | What gets built | What you can do at the end | Exit criteria |
|---|---|---|---|
| **M1 Foundation** ("walking skeleton") | Repo + engineering standards, CI, Docker dev setup, FastAPI + Next.js + PostgreSQL, migrations, tenant isolation (RLS), logging/health, OpenAPI export, bootstrap platform admin (A-03) | Open the app locally, see a health page, log in as the bootstrap admin | CI green; two-coaching isolation tests pass; restart keeps data |
| **M2 Identity & coaching admin** | Email/password + Google login, sessions, coaching creation, Owner/admin/faculty, invites (activation links), grants, ownership transfer, admin reset links, audit log | Create your coaching, invite faculty, give grants | Role/grant tests; removed user loses access immediately |
| **M3 Question authoring** | Taxonomy + exam + source + Bloom catalogues with Excel import; editor for all 9 formats; LaTeX + visual equations; images; passages; validation; codes/versions/revisions; student-style preview | Faculty enter questions by hand with equations/diagrams | All 9 formats: valid saves, invalid answers rejected (fixtures from spec-v1) |
| **M4 Review & bank** ⭐ *first real use* | Workflow (submit → QC → approve → publish, return for correction), shared queue, revision-bound approvals, diff view, history, archive/restore, bank list/filters/counts, code lookup, free-text + fuzzy search, exact/fuzzy duplicate check, in-app notifications | **Faculty start real work**: enter, review and publish questions, search the bank | Published versions immutable; stale-approval tests; search p95 measured on 1-lakh fixture |
| **M5 AI assist & prompt library** | Provider adapters (Anthropic, OpenAI, Google, OpenRouter), encrypted coaching keys, **live model catalogue** from provider APIs, model settings, AI runs + cost ledger, budgets 80/100, tagging, translation (+ glossary, "source updated" flag), solve, **AI verification** + opt-in correction, **Prompt Library** (view, personal prompts, one-off custom prompt, edit/test/activate/rollback), **Economy runs** via providers' Batch APIs (about half price, results within 24 h, in-app notification; H-18) | Use AI on questions; admins tune prompts and budgets | Every run traced to model + prompt version; budget stop works; no cross-coaching key use |
| **M6 Document ingestion v1** | Upload (PDF/DOCX/images), background jobs (progress, cancel, retry), AI page extraction to candidates with source anchors, side-by-side review screen, duplicate check, convert to questions; golden evaluation set | Upload existing papers and turn them into reviewed questions | Extraction quality measured on your sample pages; cancel/retry never loses or duplicates work |
| **M7 Hardening & cloud** | Performance pass, security review, choose AWS vs Google Cloud (short comparison doc), infrastructure as code, deploy with **managed PostgreSQL** + object storage, backup + **restore drill**, monitoring | Faculty use it from anywhere, not only your PC | Restore tested; security checklist done; owner sign-off |

Rough effort: each milestone is ~1–3 weeks of focused work for you + Claude Code. Treat that as an estimate
to refine after M1, not a commitment.

### Phase 1 explicitly does **not** include
OTP login, separate answer-key/solution file pairing, adaptive layout patterns, semantic duplicates,
knowledge-graph prerequisites/graph view, variants, diagram generation, MathML input, legacy .DOC, bulk
edits, storage dashboard/original deletion, coaching copy (all P2); tests/papers (P3); anything for students (P4+).

### Hardening track (added 23 Oct 2026, owner-approved)

Industry practices the platform was missing, found in a review of the repository on 23 Oct. They are
defined as requirements **K-01 to K-19** in [01-requirements](./01-requirements.md) (section K; the `H-xx` IDs
there belong to the AI platform). They are not product features and do not start Phase 2. Each is its own
small pull request. The first batch (K-01 to K-05) is built **now, before the rest of M3**, because it is cheap and
protects everything built after it. The rest are placed before the milestone or screen that needs them.

| ID | Practice (plain words) | When | Owner action needed | Done when |
|---|---|---|---|---|
| K-01 | **Dependabot**: GitHub proposes dependency updates as PRs every week | Now | None | `.github/dependabot.yml` merged; first update PRs appear |
| K-02 | **Code scanning (Semgrep)**: scan our own Python and TypeScript for vulnerability patterns, in CI | Now | None | New CI job green on `main`; findings triaged, none ignored silently |
| K-03 | **Backup and restore tooling**: dump a database, restore it into a fresh one, compare tables and tenant-isolation policies | Now | None | Backup and restore scripts + CI "restore drill" job green; written targets for how much data may be lost and how long recovery may take |
| K-16 | **Real scheduled backups**: daily database and file backups to an off-machine place, and a real restore of real data tested | **Before the first real coaching uses the app (M4)** | **Owner chooses the destination** (for example an S3-compatible bucket, a cloud drive or an external disk kept elsewhere) | Backups run daily without anyone remembering; one real restore done and written down |
| K-04 | **Property-based tests (Hypothesis)**: generate thousands of odd inputs for the import reader and plan engine | Now | None | Properties pass in CI; a deliberately broken reader is caught |
| K-05 | **GitHub settings checklist**: branch protection, required checks, no force-push to `main`, secret-scanning push protection | Now | **Owner applies the settings** (this session cannot see or change them) and confirms | `docs/operations/github-settings.md` merged; owner confirms each setting |
| K-10 | **Import threat model + ADR**: the Excel/CSV import already parses untrusted files inside the API process (with size, row and archive limits); decide whether that stays or moves to a separate low-resource worker | **Before the import screen (M3 PR 2d-3)**, right after K-01 to K-05 | None | ADR accepted; if it says move, the worker is built before the screen |
| K-09 | **Accessibility checks (axe)** inside the browser tests | With the next web PR after K-01 to K-05 (M3 PR 2d-2) | None | Browser tests fail on serious accessibility violations |
| K-06 | **Monitoring**: error tracking, metrics and tracing as decided in ADR-0010 | Before the first real coaching uses the app (M4 "first real use") | Sentry account/DSN when ready | Errors and slow requests visible without asking a user |
| K-07 | **Migration safety linter** (squawk) in CI | With M4 | None | An unsafe migration is rejected in CI |
| K-18 | **Property-based tests** for the answer checker and question validators | With the validators (M3 PR 3a) | None | Properties pass in CI; a deliberately broken validator is caught |
| K-19 | **Staging rehearsal** of migrations on a copy of real-shaped data | With M7 hosting | Choose hosting (M7) | Rehearsal done and documented before each production migration |
| K-08 | **Load tests (k6)** for search and listing on a one-lakh-question fixture | M4 (search exit criterion) | None | Scripts in repo; p95 numbers recorded |
| K-11 | **AI threat model**: provider prompts, one-off user prompts, AI-generated text and corrections, key handling | **Before M5** | None | Threat model reviewed; its test cases feed K-14 |
| K-17 | **Uploads threat model** and parsing of untrusted documents in a **separate low-resource worker** | Before M6 (document uploads) | None | Threat model reviewed; worker built |
| K-12 | **Feature flags**: ship a feature switched off | Before M5 | None | Small flag mechanism with tests |
| K-13 | **Service targets and alerts (SLOs)**: written uptime and speed targets with alerts | M7 | Agree the targets | Targets documented; alerts fire in a test |
| K-14 | **AI evaluation harness**: known-good examples scored on a fake provider on every PR (checks the plumbing); **any prompt or model change must also show a real-provider score** on the same examples before merge; cost tracking; prompt-injection tests | Start of M5 | Provide sample questions with known answers; accept a small API cost per prompt/model change | Harness runs in CI; the PR template asks for the real score on prompt/model changes |
| K-15 | **Privacy review** of data export and deletion for India's DPDP Act (already applies to faculty data) | Draft by M4; **sign-off before the first feature that deletes originals (P2) or exports a coaching's data (P3)**, and before any student data (P4) | **A lawyer must confirm** the details; Claude drafts only | Draft in `docs/`; legal sign-off recorded before those features ship |

Claude cannot do, and the table does not claim to do: change GitHub settings (K-05), create accounts or pick
hosting (K-06, K-16, K-19, M7), or give legal advice (K-15).

## 4. Proposed technology stack (not final, owner to confirm)

| Concern | Proposal | Why |
|---|---|---|
| Backend | **Python 3.12+, FastAPI, Pydantic v2** | Best ecosystem for PDF/OCR/AI; typed models produce the OpenAPI contract automatically |
| Database | **PostgreSQL 16+** with **pg_trgm** (fuzzy) and **pgvector** (P2 semantic) | One database for data, search and embeddings at this scale |
| DB access | **SQLAlchemy 2** + **Alembic** migrations | Mature, explicit, reviewable migrations |
| Background jobs | **PostgreSQL-backed job queue** (e.g. Procrastinate) behind our own interface | Fewer moving parts than Celery + Redis for a small team on a Windows PC; jobs are already durable in Postgres. Swap to Celery/Redis later only if measured load needs it |
| Web app | **Next.js + React + TypeScript**, Tailwind + shadcn/ui, TanStack Query, client generated from OpenAPI | Mainstream, strongly typed, fast UI work |
| Maths | **KaTeX** rendering, **MathLive** visual equation editor | Fast, consistent rendering; visual + LaTeX input |
| AI | Own adapter interface + official provider SDKs; OpenRouter via its API | No provider names in business code; easy to add providers |
| Files | Storage interface: local disk in development, S3-compatible in hosting | Same code, different backend |
| Auth | Server sessions (cookies) via reviewed libraries (argon2-cffi, Authlib for Google); token auth added in P4 | Correct for browsers now; pluggable for apps later |
| Quality | ruff, mypy, pytest (real Postgres), ESLint, Prettier, tsc strict, Playwright, import-linter | Automated "not vibe coded" guardrails |
| CI | GitHub Actions | Repo is on GitHub |
| Local dev | Docker Desktop + WSL2 on Windows (`docker compose up`) | Same Linux environment everywhere |
| Observability | Structured JSON logs, OpenTelemetry, Sentry (free tier) | See and debug the running system |

## 5. How we will work (Claude Code + you + Codex)

1. Each milestone starts with a short **design note** (screens, API, tables) for your approval.
2. Claude Code builds it in small **pull requests** on a feature branch, with tests, never pushing straight to `main`.
3. CI must be green. **Codex reviews** the PR (optional), and you check behaviour in the running app.
4. **You merge.** Decisions go into ADRs; docs are updated in the same PR.

## 6. Pre-M1 deliverables (done 18 Oct, awaiting approval)

1. `docs/engineering/standards.md`: repo layout, coding rules, testing, CI, PR rules.
2. `AGENTS.md` / `CLAUDE.md`: rules every AI coding agent follows in this repo.
3. `docs/architecture/api-style-guide.md`: API conventions (errors, pagination, versioning, auth for many clients).
4. ADRs: stack, multi-client API/auth, job queue, search, observability, tenant isolation.
5. M1 design note.

## 7. Owner answers (18 Oct 2026)

| Question | Answer |
|---|---|
| Who builds | Owner + Claude Code; Codex may review |
| Prompts | "QC prompt" = AI verification prompt. Users can view it, save their own, use a one-off prompt, and pick the model per run (live provider list) |
| Hosting | Develop on owner's PC; later cloud (AWS or Google Cloud) incl. managed database (decided in M7) |
| Samples | Owner uploads real files through the app during M6 |
| OTP + self-service reset | Phase 2 |
| Next phase after P1 | P2 |
| Cheap, slow AI runs (19 Oct) | Economy (batch) runs in P1/M5; user chooses per run, admins set defaults; in-app notification when done (H-18) |

## 8. Open questions

None blocking. M1 and M2 are built. Next: the owner checks M2 with the [M2 demo](../operations/m2-demo.md)
(and, optionally, turns on Google login with its [setup guide](../operations/google-login.md)). The [M3 design note](../architecture/m3-design-note.md)
(question authoring) is being built (the Syllabus screen is merged). The hardening track above
(K-01 to K-05, then K-10) is built before the rest of M3.
