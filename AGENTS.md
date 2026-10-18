# AGENTS.md: Rules for AI coding agents (Claude Code, Codex, others)

This repository is a multi-coaching **question bank platform** (FastAPI + PostgreSQL backend, Next.js web).
Humans must be able to read, own and maintain every line. Follow these rules on every task.

## 1. Read before you write
1. `docs/product/01-requirements.md`: requirement IDs (A-01, D-02, H-13…) and phases. Build only what the current milestone needs.
2. `docs/product/02-phase-plan.md`: current milestone and its exit criteria.
3. `docs/engineering/standards.md`: layout, coding, security, testing, Definition of Done.
4. `docs/architecture/api-style-guide.md` and `docs/architecture/adr/`: API rules and decisions.
5. The milestone design note in `docs/architecture/` (e.g. `m1-design-note.md`).
`docs/spec-v0/` and `docs/spec-v1/` are **reference input only**. Never edit them, and don't treat them as current requirements.

## 2. How to work
- One story/requirement per pull request; aim for < 400 changed lines. Never push to `main`.
- Write tests together with the code; bug fixes start with a failing test.
- Run the checks below before saying anything is done, and **report the actual commands and results**.
  Never claim a test passed that you did not run. Say clearly what you could not verify.
- If the spec is ambiguous or contradicts an ADR, stop and ask the owner. Don't guess on product behaviour.
- A significant technical decision needs an ADR (new file, or superseding one).
- Update docs in the same PR when behaviour, setup or API changes.

## 3. Never
- Never weaken tenant isolation, RLS policies, permission checks or validators to make a test pass.
- Never trust an organization ID, role or grant sent by a client; resolve them server-side.
- Never build SQL with string concatenation; never use floats for money or numerical answers.
- Never commit secrets, real API keys, real coaching content or `.env` files.
- Never render question content as raw HTML; never execute content from documents or AI output.
- Never put business logic in the web app or in Next.js server code that bypasses `/api/v1`.
- Never import another module's internals or tables; use its `public.py`.
- Never edit an applied migration; add a new one.
- Never disable, skip or delete a failing test to get green.

## 4. Checks to run (from repo root)
```bash
# backend (services/api)
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports
uv run pytest
# web (apps/web)
pnpm lint && pnpm typecheck && pnpm test && pnpm build
# contract
make openapi-check
```
(Exact commands are kept current in `README.md` once code exists.)

## 5. Definition of Done
See `docs/engineering/standards.md` §11. In short: requirement IDs referenced, tests written and run, permissions and
tenant isolation tested, audit events, safe migration, logs/metrics, OpenAPI + client updated, docs updated.

## 6. Commit and PR format
- Conventional commits: `feat(questions): add numerical answer validator`.
- PR body follows `.github/pull_request_template.md`.
