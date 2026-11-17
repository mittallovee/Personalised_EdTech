#!/usr/bin/env bash
# K-08: build the load-test database, fill it with synthetic questions, and serve the API on :8090.
# Runs inside a throwaway python:3.14-slim container; see docs/operations/load-tests.md.
#
#   /src   the repository (read only is enough; it is copied)
#   /load  a folder of yours: load-users.json is written there for the k6 script
#
# Environment:
#   LOAD_TEST_PASSWORD   password of the seeded load-test members (12+ characters, made up)
#   QBANK_TEST_ADMIN_URL owner connection to the PostgreSQL server (its "postgres" database)
#   QUESTIONS            how many questions (default 100000)
#   SKIP_SEED=1          keep the existing qbank_load database; only migrate it and serve
set -euo pipefail
: "${LOAD_TEST_PASSWORD:?set LOAD_TEST_PASSWORD}"
: "${QBANK_TEST_ADMIN_URL:?set QBANK_TEST_ADMIN_URL}"
export UV_HTTP_TIMEOUT=900 UV_LINK_MODE=copy
pip install -q uv >/dev/null 2>&1
mkdir -p /repo
cd /src
tar --exclude=.git --exclude=node_modules --exclude=.venv --exclude=.next -cf - . | tar -xf - -C /repo
cd /repo/services/api
uv sync --frozen >/tmp/sync.log 2>&1 || { tail -20 /tmp/sync.log; exit 1; }

# Creates (or, with SKIP_SEED=1, only migrates) qbank_load and prints its owner and app URLs.
uv run python - <<'PY' > /tmp/urls
import os, sys, time
from alembic import command
from sqlalchemy.engine import make_url
from tests.integration.conftest import (
    ADMIN_URL, APP_PASSWORD, APP_ROLE, alembic_config, create_database, drop_database,
)
if os.environ.get("SKIP_SEED") == "1":
    url = make_url(ADMIN_URL).set(database="qbank_load")
    owner = url.render_as_string(hide_password=False)
    app = url.set(username=APP_ROLE, password=APP_PASSWORD).render_as_string(hide_password=False)
else:
    drop_database("qbank_load")
    owner, app, _ = create_database("qbank_load")
began = time.monotonic()
command.upgrade(alembic_config(owner), "head")
print(f"migrated in {time.monotonic() - began:.1f}s", file=sys.stderr)
print(owner)
print(app)
PY
OWNER_URL="$(sed -n 1p /tmp/urls)"
APP_URL="$(sed -n 2p /tmp/urls)"

if [ "${SKIP_SEED:-}" != "1" ]; then
  echo "--- seeding ${QUESTIONS:-100000} questions"
  MIGRATION_DATABASE_URL="$OWNER_URL" uv run python -m tests.load.seed_bank \
    --questions "${QUESTIONS:-100000}" --users-out /load/load-users.json
fi

echo "--- serving on :8090"
# The per-person search limit is for real people; the load test measures the database and the API.
export DATABASE_URL="$APP_URL" APP_ENV=local SESSION_COOKIE_SECURE=false LOG_LEVEL=WARNING \
  SEARCHES_PER_USER=1000000 LOGIN_ATTEMPTS_PER_IP=100000 LOGIN_ATTEMPTS_PER_EMAIL=100000
exec uv run uvicorn qbank.main:create_app --factory --host 0.0.0.0 --port 8090 \
  --no-proxy-headers --log-level warning
