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
# A statement longer than 500 characters before the keyword is still read to its semicolon.
psql <<'SQL'
# ruleid: qbank-no-rls-bypass-infra
ALTER ROLE app
    -- option note 00: kept on its own line to make the statement long
    -- option note 01: kept on its own line to make the statement long
    -- option note 02: kept on its own line to make the statement long
    -- option note 03: kept on its own line to make the statement long
    -- option note 04: kept on its own line to make the statement long
    -- option note 05: kept on its own line to make the statement long
    -- option note 06: kept on its own line to make the statement long
    -- option note 07: kept on its own line to make the statement long
    -- option note 08: kept on its own line to make the statement long
    -- option note 09: kept on its own line to make the statement long
    -- option note 10: kept on its own line to make the statement long
    -- option note 11: kept on its own line to make the statement long
    BYPASSRLS;
SQL
# ruleid: qbank-no-rls-bypass-infra
psql -c "ALTER ROLE app PASSWORD 'safe;value' BYPASSRLS;"
# ruleid: qbank-no-rls-bypass-infra
psql -c "ALTER ROLE \"odd;name\" BYPASSRLS"
psql <<'SQL'
# ruleid: qbank-no-rls-bypass-infra
ALTER ROLE app -- backup access; reviewed
BYPASSRLS;
SQL
# ruleid: qbank-no-rls-bypass-infra
psql -c "ALTER ROLE app /* a; b */ BYPASSRLS;"
# ruleid: qbank-no-rls-bypass-infra
psql -c 'ALTER ROLE app PASSWORD $$a;b$$ BYPASSRLS;'
# ruleid: qbank-no-rls-bypass-infra
psql -c 'ALTER ROLE app PASSWORD $t$a;b$t$ BYPASSRLS;'
# ruleid: qbank-no-rls-bypass-infra
psql -c 'ALTER ROLE app PASSWORD $tag1$a;b$tag1$ BYPASSRLS;'
# ruleid: qbank-no-rls-bypass-infra
psql -c "ALTER /* managed */ ROLE app BYPASSRLS;"
psql <<'SQL'
# ruleid: qbank-no-rls-bypass-infra
CREATE -- managed
USER app BYPASSRLS;
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
