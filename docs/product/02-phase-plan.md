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

The order of P3–P8 can change; we re-plan after each phase with real usage data.

## 3. Phase 1 — Question Bank Core (in detail)

**Goal:** a coaching can put its existing and new Physics questions into a clean, reviewed, searchable bank,
with AI doing the heavy lifting and humans in control.

| Milestone | What gets built | What you can do at the end | Exit criteria |
|---|---|---|---|
| **M1 Foundation** ("walking skeleton") | Repo + engineering standards, CI, Docker dev setup, FastAPI + Next.js + PostgreSQL, migrations, tenant isolation (RLS), logging/health, OpenAPI export, bootstrap platform admin (A-03) | Open the app locally, see a health page, log in as the bootstrap admin | CI green; two-coaching isolation tests pass; restart keeps data |
| **M2 Identity & coaching admin** | Email/password + Google login, sessions, coaching creation, Owner/admin/faculty, invites (activation links), grants, ownership transfer, admin reset links, audit log | Create your coaching, invite faculty, give grants | Role/grant tests; removed user loses access immediately |
| **M3 Question authoring** | Taxonomy + exam + source + Bloom catalogues with Excel import; editor for all 9 formats; LaTeX + visual equations; images; passages; validation; codes/versions/revisions; student-style preview | Faculty enter questions by hand with equations/diagrams | All 9 formats: valid saves, invalid answers rejected (fixtures from spec-v1) |
| **M4 Review & bank** ⭐ *first real use* | Workflow (submit → QC → approve → publish, return for correction), shared queue, revision-bound approvals, diff view, history, archive/restore, bank list/filters/counts, code lookup, free-text + fuzzy search, exact/fuzzy duplicate check, in-app notifications | **Faculty start real work**: enter, review and publish questions, search the bank | Published versions immutable; stale-approval tests; search p95 measured on 1-lakh fixture |
| **M5 AI assist & prompt library** | Provider adapters (Anthropic, OpenAI, Google, OpenRouter), encrypted coaching keys, model settings, AI runs + cost ledger, budgets 80/100, tagging, translation (+ glossary, "source updated" flag), solve, check + opt-in correction, **Prompt Library** (view/edit/test/activate/rollback) | Use AI on questions; admins tune prompts and budgets | Every run traced to model + prompt version; budget stop works; no cross-coaching key use |
| **M6 Document ingestion v1** | Upload (PDF/DOCX/images), background jobs (progress, cancel, retry), AI page extraction to candidates with source anchors, side-by-side review screen, duplicate check, convert to questions; golden evaluation set | Upload existing papers and turn them into reviewed questions | Extraction quality measured on your sample pages; cancel/retry never loses or duplicates work |
| **M7 Hardening & first hosting** | Performance pass, security review, backup + **restore drill**, monitoring, deploy to a small cloud server (or office machine) | Faculty use it from anywhere, not only your PC | Restore tested; security checklist done; owner sign-off |

Rough effort: each milestone is ~1–3 weeks of focused work for you + Claude Code. Treat that as an estimate
to refine after M1, not a commitment.

### Phase 1 explicitly does **not** include
OTP login, separate answer-key/solution file pairing, adaptive layout patterns, semantic duplicates,
knowledge-graph prerequisites/graph view, variants, diagram generation, MathML input, legacy .DOC, bulk
edits, storage dashboard/original deletion, coaching copy (all P2); tests/papers (P3); anything for students (P4+).

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

## 6. Next deliverables (before M1 code)

1. `docs/engineering/standards.md`: repo layout, coding rules, testing, CI, PR rules.
2. `AGENTS.md` / `CLAUDE.md`: rules every AI coding agent follows in this repo.
3. `docs/architecture/api-style-guide.md`: API conventions (errors, pagination, versioning, auth for many clients).
4. ADRs: stack, multi-client API/auth, job queue, search, observability, tenant isolation.
5. M1 design note.

## 7. Open questions for the owner

1. **Prompt permissions**: OK that all faculty can *view* prompts, and only admins (plus faculty given
   `MANAGE_AI_PROMPTS`) can edit/activate? Should individual faculty also have *personal* prompt versions?
   *(Recommendation: no personal versions. Per-run extra instructions cover that need, and one shared
   version keeps quality consistent.)*
2. **"QC prompts"**: you meant the AI answer/solution **check**, right? (Human QC has no prompt.)
3. **Hosting for M7**: are faculty working in the same office as your PC, or do they need internet access
   (small cloud server, roughly a few thousand rupees per month)?
4. **Samples**: can you share 30–50 representative pages (printed, scanned, handwritten, Hindi) before M6?
   They become our golden evaluation set.
5. **OTP and self-service password reset in Phase 2**: OK? (Phase 1 uses admin-generated links and Google login.)
6. **After Phase 1**: is the next priority P2 (better ingestion/AI) or P3 (tests & papers)?
