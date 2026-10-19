#!/bin/sh
# Ensures the restricted runtime roles exist (ADR-0005). Runs as the `db-init` compose service on every
# `docker compose up`, before migrations, so it works for new and already-existing database volumes.
#
# - qbank_app:    used by the API.
# - qbank_worker: used by the background worker. A member of qbank_app (same tenant-restricted table
#                 access) plus, granted by migrations, the cross-coaching jobs_* functions the API
#                 must not have.
# Both can log in but own nothing, are not superusers and cannot bypass row-level security;
# migrations grant exactly the privileges they need. Passwords follow APP_DB_PASSWORD and
# WORKER_DB_PASSWORD in .env. In the cloud these roles are created once by infrastructure code instead.
#
# Connection comes from the standard PG* environment variables (PGHOST, PGUSER, PGPASSWORD, PGDATABASE).
set -eu
psql -v ON_ERROR_STOP=1 \
    -v app_password="$APP_DB_PASSWORD" -v worker_password="$WORKER_DB_PASSWORD" <<'SQL'
SELECT format(
    CASE WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r.name) THEN 'ALTER' ELSE 'CREATE' END
    || ' ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE',
    r.name, r.password)
FROM (VALUES ('qbank_app', :'app_password'), ('qbank_worker', :'worker_password'))
    AS r (name, password)
\gexec
SELECT 'GRANT qbank_app TO qbank_worker'
WHERE NOT pg_has_role('qbank_worker', 'qbank_app', 'MEMBER')
\gexec
SQL
echo "qbank_app and qbank_worker roles ready"
