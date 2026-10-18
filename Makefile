# Common commands. On Windows, run these inside WSL2 (Ubuntu), where `make` is available.
.PHONY: install check backend-check web-check format up down logs

install:            ## Install backend and web dependencies
	cd services/api && uv sync
	pnpm install

check: backend-check web-check   ## Run every check CI runs

# Integration tests need PostgreSQL: start it with `docker compose up -d postgres` and
# copy .env.example to .env (its QBANK_TEST_* values point at that server).
backend-check:
	cd services/api && uv run ruff check . && uv run ruff format --check . \
		&& uv run mypy && uv run lint-imports \
		&& { set -a; [ ! -f ../../.env ] || . ../../.env; set +a; } && uv run pytest

web-check:
	pnpm lint && pnpm typecheck && pnpm format:check && pnpm build

format:             ## Auto-format all code
	cd services/api && uv run ruff format . && uv run ruff check --fix .
	pnpm -r format

up:                 ## Start the local stack
	docker compose up --build -d

down:               ## Stop the local stack (data is kept)
	docker compose down

logs:
	docker compose logs -f
