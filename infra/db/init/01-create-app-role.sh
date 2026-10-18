#!/bin/sh
# Runs once, when the local PostgreSQL volume is first created (docker-entrypoint-initdb.d).
# Creates the restricted runtime role used by the API and worker (ADR-0005): it can log in but
# owns nothing, is not a superuser and cannot bypass row-level security. Migrations grant it
# exactly the privileges it needs. In the cloud this role is created once by infrastructure code.
set -eu
psql -v ON_ERROR_STOP=1 -v app_password="$APP_DB_PASSWORD" \
     --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE qbank_app LOGIN PASSWORD :'app_password' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
SQL
