# Test file for rules/python.yml. A comment line saying ruleid (then the rule name) marks the next
# line as one that must be flagged; one saying ok marks a line that must not be. Run:
#   semgrep --test --config .semgrep/rules .semgrep/tests
from sqlalchemy import Float, Numeric, text
import sqlalchemy as sa


def sql(name: str, log, logger) -> None:
    # ruleid: qbank-sql-text-built-from-string
    text(f"SELECT * FROM t WHERE name = '{name}'")
    # ruleid: qbank-sql-text-built-from-string
    text("SELECT * FROM t WHERE name = '" + name + "'")
    # ruleid: qbank-sql-text-built-from-string
    text("SELECT * FROM t WHERE name = '%s'" % name)
    # ruleid: qbank-sql-text-built-from-string
    text("SELECT * FROM t WHERE name = '{}'".format(name))
    # ok: qbank-sql-text-built-from-string
    text("SELECT * FROM t WHERE name = :name")

    # ruleid: qbank-no-float-column
    sa.Float()
    # ruleid: qbank-no-float-column
    Float(asdecimal=False)
    # ok: qbank-no-float-column
    Numeric(12, 2)

    # ruleid: qbank-no-secret-in-log
    log.info("login", password=name)
    # ruleid: qbank-no-secret-in-log
    logger.warning("reset", reset_token=name)
    # ruleid: qbank-no-secret-in-log
    log.error("x", api_key=name)
    # ok: qbank-no-secret-in-log
    log.info("login", user_id=name)
    # ok: qbank-no-secret-in-log
    other.info("login", password=name)


# ruleid: qbank-no-rls-bypass
ROLE = "CREATE ROLE app LOGIN BYPASSRLS"
# ruleid: qbank-no-rls-bypass
ALTERED = "alter role app with bypassrls"
# ruleid: qbank-no-rls-bypass
QUOTED = 'ALTER ROLE "qbank_app" BYPASSRLS'
# ruleid: qbank-no-rls-bypass
QUOTED_CLAUSE = "ALTER ROLE \"qbank_app\" WITH LOGIN PASSWORD 'secret' BYPASSRLS"
# ruleid: qbank-no-rls-bypass
SPLIT = "CREATE ROLE app LOGIN " "BYPASSRLS"
# ruleid: qbank-no-rls-bypass
MULTI = """ALTER ROLE app
    LOGIN
    BYPASSRLS"""
# ruleid: qbank-no-rls-bypass
LONG = """ALTER ROLE app
    WITH
    LOGIN
    PASSWORD 'x'
    CONNECTION LIMIT 5
    BYPASSRLS;"""
# ruleid: qbank-no-rls-bypass
FORMATTED = f"ALTER ROLE {ROLE} WITH BYPASSRLS"
# ruleid: qbank-no-rls-bypass
OFF = "SET row_security = off"
# ruleid: qbank-no-rls-bypass
DROP = "ALTER TABLE t DISABLE ROW LEVEL SECURITY"
# ruleid: qbank-no-rls-bypass
UNFORCE = "ALTER TABLE t NO FORCE ROW LEVEL SECURITY"
# ok: qbank-no-rls-bypass
SAFE = "CREATE ROLE app LOGIN NOSUPERUSER NOBYPASSRLS"
# ok: qbank-no-rls-bypass
FORCE = "ALTER TABLE t FORCE ROW LEVEL SECURITY"
# ok: qbank-no-rls-bypass
READ = "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
# ok: qbank-no-rls-bypass
TALK = "The backup role must be a superuser or have BYPASSRLS."
# ok: qbank-no-rls-bypass
OTHER_STATEMENT = "CREATE ROLE app LOGIN; SELECT 'a role with BYPASSRLS would be bad'"
