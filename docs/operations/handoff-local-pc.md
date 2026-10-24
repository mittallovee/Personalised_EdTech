# Handoff: continuing on the owner's PC

Written at the end of the cloud session (2026-10-24) so a new Claude Code session, started in a local clone, can pick
up exactly where this one stopped. A "handoff" is a note that lets a new worker continue without the old worker's
memory. Read `CLAUDE.md`, `AGENTS.md` and `docs/product/02-phase-plan.md` first; this note only adds what they do not say.

## Standing instructions from the owner
- **Phase 1 is M1 to M7. Do not start Phase 2 automatically.** The owner tests Phase 1 and approves Phase 2.
- The owner is learning industry practice: explain each new technical term in one short phrase, and end every task with
  what changed, requirement IDs covered, checks actually run (with results) and what remains.
- Workflow: Claude writes code, Codex reviews each pull request automatically, the owner merges. One requirement per PR.
- The owner now tests by hand on their own PC (`docker compose up --build`, http://localhost:3000; see README).

## Where things stand
- Done and merged: M1, M2; M3 up to the syllabus import apply (2c-3); hardening K-01 to K-05, K-10, K-10a; the
  Dependabot updates (setup-uv 10, upload-artifact 7, pnpm/action-setup 6.1, uv 0.12, uv_build <0.14, ESLint 10).
- **Open: PR #58 (K-10b, expiry of unapplied import previews, migration 0018).** All 8 CI checks green, Codex found
  no major issues, all threads resolved. The owner merges it. If it is not merged yet, merge it before new work.
- Dependabot PRs #46 (TypeScript 7), #41 (Node 25), #48 (@types/node 26) were closed on purpose and set to ignore
  that major version: TypeScript 7 breaks web lint; Node 25 is not LTS and its image lacks corepack; @types/node 26
  does not match the Node 22 runtime. A permanent `ignore:` entry in `.github/dependabot.yml` is still to do.

## Next work, in order
1. **M3 2d-2**: concepts and aliases screens, Exams and sources screens, with K-09 axe accessibility checks in the
   browser tests.
2. **M3 2d-3**: syllabus import screen. In its browser test, check the web same-origin proxy with a 5 MB and a slow
   upload; browser tests may need `IMPORT_UPLOADS_PER_USER` raised (the limit is 10 per 10 minutes per user).
3. M3 3a to 3i (questions; K-18 property tests for validators go with 3a), then PR 4 demo notes.
4. Hardening still to build, with deadlines in the phase plan: K-06 monitoring, K-07 migration linter, K-08 k6 load
   tests, K-11 AI threat model (before M5), K-12 flags, K-13 SLOs, K-14 AI eval harness, K-15 privacy review,
   K-16 scheduled off-machine backups (owner chooses the destination; before M4), K-17 uploads threat model and
   worker (before M6), K-19 staging rehearsal (M7).

## Owner items still open
- Apply the GitHub settings in `docs/operations/github-settings.md` (K-05) and tell Claude "settings done".
- A queued idea: control characters in M2 display names (not yet a PR).
- The owner's real syllabus Excel is not in the repo (never commit real coaching content). The 5,000-row apply cap
  can be changed if the real file is larger.
- One Codex finding on PR #37 was deliberately left open (owner chose option A).

## Practical lessons from the cloud sessions
- Integration tests need PostgreSQL: `docker compose up -d postgres`, then `make check`. If the database user is a
  superuser it ignores row-level security, so tests that look at rows directly must filter by organization.
- The API contract check (oasdiff) treats adding a value to a response enum as a breaking change; add a new
  documented error response (like `410 IMPORT_EXPIRED`) instead.
- Prove each new test can fail: break the code on purpose, watch it fail, restore from a saved copy (do not use
  `git checkout -- <dir>` as the restore; it throws away uncommitted work).
- Do not use `pkill -f` in a command that contains the pattern; it kills your own shell.
- Codex reviews are strict and usually right; each finding gets a fix plus a test, or a short written reason.
