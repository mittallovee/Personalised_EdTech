# Personalised EdTech: Question Bank Platform

A multi-coaching platform where faculty create and import questions (PDF/Word/images), AI helps tag, translate,
solve and verify them, and reviewed questions are published into a versioned, searchable bank. Later phases add
tests and papers, student apps, live exams, analytics, courses and personalized AI teaching on the same API.

**Status:** Phase 1, milestones M1 (foundation) and M2 (identity & coaching admin) built; check them yourself with the [M1 demo](docs/operations/m1-demo.md) and the [M2 demo](docs/operations/m2-demo.md).
Next: you check M2, then M3 (question authoring) starts with its design note for your approval. Designs: [M1](docs/architecture/m1-design-note.md), [M2](docs/architecture/m2-design-note.md).

## Documentation
- Start here: [`docs/README.md`](docs/README.md)
- What we build first: [`docs/product/04-phase-1-scope.md`](docs/product/04-phase-1-scope.md)
- Engineering rules: [`docs/engineering/standards.md`](docs/engineering/standards.md) · [`AGENTS.md`](AGENTS.md)

## Repository layout
| Path | What |
|---|---|
| `services/api/` | Python backend: FastAPI API and background worker (`python -m qbank.worker`) |
| `apps/web/` | Next.js + TypeScript web app for faculty and admins |
| `apps/e2e/` | Browser tests (Playwright): a real Chromium drives the running app |
| `infra/docker/` | Dockerfiles |
| `infra/scripts/` | Operational scripts, e.g. the restart check (`make restart-check`) |
| `infra/db/` | Script that creates/updates the restricted database roles `qbank_app` and `qbank_worker` (`db-init` service) |
| `compose.yaml` | Local stack: PostgreSQL, role setup, migrations, API, worker, web |
| `docs/` | Requirements, architecture decisions, standards |

## Run it locally (Windows PC with Docker Desktop)
Prerequisites: **Docker Desktop** (WSL2 backend) and **Git**.

```bash
# In a WSL2 (Ubuntu) terminal. Keeping the code inside the Linux filesystem (e.g. ~/code) is much faster.
git clone https://github.com/mittallovee/Personalised_EdTech.git
cd Personalised_EdTech
cp .env.example .env          # local settings; never commit .env
docker compose up --build     # first run downloads images and takes a few minutes
```

Create your platform admin account (once):

```bash
docker compose run --rm migrate qbank create-platform-admin --email you@example.com --name "Your Name"
# asks for a password (min 12 characters) twice
```

Then view and test it:
1. Open **http://localhost:3000**: you are sent to the sign-in page.
2. Sign in with the admin email and password: the home page shows your name, "Platform admin" and
   system health (API, database, migrations all `ok`).
3. A wrong password shows one generic message; after 5 wrong tries the account is locked for 15 minutes.
4. **Sign out**: you are back on the sign-in page and the home page is no longer reachable.
5. Restart check (data survives `docker compose down` + `up`):
   `QBANK_CHECK_EMAIL=you@example.com make restart-check`, which asks for your password and ends with `PASS`.

The full M1 walkthrough, with what each check proves, is in [`docs/operations/m1-demo.md`](docs/operations/m1-demo.md).
To try creating a coaching, inviting faculty, roles, grants and the audit log, follow [`docs/operations/m2-demo.md`](docs/operations/m2-demo.md).

Useful addresses: API readiness http://localhost:8000/health/ready · API docs (local only)
http://localhost:8000/api/docs. To open the app on your own domain, see
[`docs/operations/remote-access.md`](docs/operations/remote-access.md).
To let people sign in with Google, follow [`docs/operations/google-login.md`](docs/operations/google-login.md)
(off until you do; the app works with passwords without it).

Stop with `Ctrl+C` or `docker compose down`. Database data is kept in a Docker volume between runs
(`docker compose down -v` deletes it). After pulling new code, run `docker compose up --build -d` again:
it rebuilds the images and applies new database migrations automatically.

## Developer checks (optional on your PC; CI runs them on every pull request)
Needs [uv](https://docs.astral.sh/uv/), Node.js 22 and pnpm (`corepack enable`).

```bash
make install                  # install backend + web dependencies
docker compose up -d postgres # integration tests need PostgreSQL (uses the values in .env)
make check                    # everything CI runs: lint, format, types, import rules, tests, build
make openapi                  # after changing the API: regenerate api/openapi.json and commit it
make format                   # auto-fix formatting
```

Backend tests are in `services/api/tests/`: `unit/` and `api/` need nothing; `integration/` creates and
drops its own temporary database on the PostgreSQL server named by `QBANK_TEST_ADMIN_URL`.

Browser tests (need the stack running and a platform admin, see [`apps/e2e/README.md`](apps/e2e/README.md)):

```bash
pnpm --filter @qbank/e2e exec playwright install chromium   # once
E2E_ADMIN_EMAIL=you@example.com E2E_ADMIN_PASSWORD='…' pnpm --filter @qbank/e2e e2e
```
