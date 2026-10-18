# ADR-0002: Modular monolith with a separate worker process
- Status: Proposed · Date: 2026-10-18
## Context
One small team, a domain still evolving, strong need for transactions across questions/reviews/audit. Long-running work (extraction, AI) must not block web requests.
## Decision
One Python codebase deployed as two process types: **API** (FastAPI) and **worker** (background jobs). Internally split into bounded-context modules with enforced boundaries (`public.py` only, import-linter). No microservices in Phase 1.
## Consequences
+ Simple to run, debug and deploy; single database transactions.
+ Workers scale independently of the API.
− Discipline needed to keep modules separate (enforced in CI).
Extraction candidates later: the live-exam engine (Phase 5) will likely be a separate service because its load pattern differs.
## Alternatives
Microservices (rejected: operational cost, distributed transactions, premature). Single process with in-request processing (rejected: blocks UI, no retries).
