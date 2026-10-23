#!/usr/bin/env bash
# Test file for rules/shell.yml (the annotations work as described in python.py).

# ruleid: qbank-no-rls-bypass-infra
psql -c "CREATE ROLE backup LOGIN BYPASSRLS"
# ruleid: qbank-no-rls-bypass-infra
psql -c 'ALTER ROLE "qbank_app" BYPASSRLS'
# ruleid: qbank-no-rls-bypass-infra
psql -c "ALTER ROLE app
    WITH
    LOGIN
    PASSWORD 'x'
    CONNECTION LIMIT 5
    BYPASSRLS;"
psql <<'SQL'
# ruleid: qbank-no-rls-bypass-infra
ALTER ROLE app
BYPASSRLS;
SQL
# ruleid: qbank-no-rls-bypass-infra
psql -c "SET row_security = off"
# ok: qbank-no-rls-bypass-infra
psql -c "CREATE ROLE app LOGIN NOSUPERUSER NOBYPASSRLS;"
# ok: qbank-no-rls-bypass-infra
psql -At -c "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
# ok: qbank-no-rls-bypass-infra
echo "Use a superuser or a role with BYPASSRLS."
# ok: qbank-no-rls-bypass-infra
psql -c "CREATE ROLE app LOGIN;"
echo "A role with BYPASSRLS can read every coaching."
