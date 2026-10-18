# Personalised EdTech: Question Bank Platform

A multi-coaching platform where faculty create and import questions (PDF/Word/images), AI helps tag, translate,
solve and verify them, and reviewed questions are published into a versioned, searchable bank. Later phases add
tests and papers, student apps, live exams, analytics, courses and personalized AI teaching on the same API.

**Status:** Phase 1, milestone M1 (foundation) in progress. See [`docs/architecture/m1-design-note.md`](docs/architecture/m1-design-note.md).

## Documentation
- Start here: [`docs/README.md`](docs/README.md)
- What we build first: [`docs/product/04-phase-1-scope.md`](docs/product/04-phase-1-scope.md)
- Engineering rules: [`docs/engineering/standards.md`](docs/engineering/standards.md) · [`AGENTS.md`](AGENTS.md)

## Repository layout
| Path | What |
|---|---|
| `services/api/` | Python backend: FastAPI API and background worker (`python -m qbank.worker`) |
| `apps/web/` | Next.js + TypeScript web app for faculty and admins |
| `infra/docker/` | Dockerfiles |
| `infra/db/` | Script that creates/updates the restricted database role (`db-init` service) |
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

Then open:
- Web app: http://localhost:3000
- API health: http://localhost:8000/health/live → `{"status":"ok"}`
- API readiness: http://localhost:8000/health/ready → database reachable and schema up to date
- API docs (local only): http://localhost:8000/api/docs

Create your platform admin account (once):

```bash
docker compose run --rm migrate qbank create-platform-admin --email you@example.com --name "Your Name"
# asks for a password (min 12 characters) twice
```

Stop with `Ctrl+C` or `docker compose down`. Database data is kept in a Docker volume between runs.

## Developer checks (optional on your PC; CI runs them on every pull request)
Needs [uv](https://docs.astral.sh/uv/), Node.js 22 and pnpm (`corepack enable`).

```bash
make install                  # install backend + web dependencies
docker compose up -d postgres # integration tests need PostgreSQL (uses the values in .env)
make check                    # everything CI runs: lint, format, types, import rules, tests, build
make format                   # auto-fix formatting
```

Backend tests are in `services/api/tests/`: `unit/` and `api/` need nothing; `integration/` creates and
drops its own temporary database on the PostgreSQL server named by `QBANK_TEST_ADMIN_URL`.
