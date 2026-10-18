#!/bin/sh
# Ensures the restricted runtime role exists (ADR-0005). Runs as the `db-init` compose service on every
# `docker compose up`, before migrations, so it works for new and already-existing database volumes.
#
# The role can log in but owns nothing, is not a superuser and cannot bypass row-level security;
# migrations grant it exactly the privileges it needs. Its password follows APP_DB_PASSWORD in .env.
# In the cloud this role is created once by infrastructure code instead.
#
# Connection comes from the standard PG* environment variables (PGHOST, PGUSER, PGPASSWORD, PGDATABASE).
set -eu
psql -v ON_ERROR_STOP=1 -v app_password="$APP_DB_PASSWORD" <<'SQL'
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'qbank_app')
    THEN format('ALTER ROLE qbank_app LOGIN PASSWORD %L '
                'NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE', :'app_password')
    ELSE format('CREATE ROLE qbank_app LOGIN PASSWORD %L '
                'NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE', :'app_password')
END
\gexec
SQL
echo "qbank_app role ready"
