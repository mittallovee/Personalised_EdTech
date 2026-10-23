"""K-03: a backup can be restored, and the restored copy keeps every tenant protection.

This is the restore drill (docs/operations/backup-and-restore.md): it runs the real
``infra/scripts/backup-db.sh`` and ``restore-db.sh`` against the migrated test database, then
compares the original and the restored copy (tables, columns, row counts, indexes, constraints,
functions, row-level-security flags and policies, privileges of the runtime roles) and checks, as
the runtime role, that one coaching still cannot see another's rows.

It needs the PostgreSQL client tools matching the server (``pg_dump`` and ``pg_restore``), or Docker
with PG_DOCKER_IMAGE set to a matching image (for example postgres:17). Without either it fails; it
does not skip, because a backup nobody can test is not a backup.
"""

import os
import secrets
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from psycopg import sql
from sqlalchemy import select
from sqlalchemy.engine import make_url

from qbank.core.db import Database
from qbank.core.tenancy import NO_CONTEXT
from qbank.modules.organizations.models import Organization
from tests.integration.conftest import (
    ADMIN_URL,
    APP_PASSWORD,
    APP_ROLE,
    WORKER_ROLE,
    Coaching,
    MigratedDatabase,
    drop_database,
)

SCRIPTS = Path(__file__).resolve().parents[4] / "infra" / "scripts"


def _client_tools_available() -> bool:
    if os.environ.get("PG_DOCKER_IMAGE"):
        return shutil.which("docker") is not None
    return shutil.which("pg_dump") is not None and shutil.which("pg_restore") is not None


@pytest.fixture(autouse=True)
def _need_client_tools() -> None:
    if not _client_tools_available():
        pytest.fail(
            "The restore drill needs pg_dump and pg_restore on PATH (same major version as the "
            "server), or Docker with PG_DOCKER_IMAGE=postgres:<server major version>."
        )


def _connection_env(
    database: str, *, user: str | None = None, password: str | None = None
) -> dict[str, str]:
    admin = make_url(ADMIN_URL)
    return {
        **os.environ,
        "PGHOST": admin.host or "localhost",
        "PGPORT": str(admin.port or 5432),
        "PGUSER": user or str(admin.username),
        "PGPASSWORD": password if password is not None else str(admin.password),
        "PGDATABASE": database,
    }


def _run(script: str, *args: object, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - our own scripts, with arguments this test builds
        [str(SCRIPTS / script), *map(str, args)],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )


@pytest.fixture(scope="module")
def backup(migrated_database: MigratedDatabase, tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("backup") / "drill.dump"
    result = _run("backup-db.sh", path, env=_connection_env(migrated_database.name))
    assert result.returncode == 0, result.stderr
    return path


@pytest.fixture
def restored_name() -> Iterator[str]:
    name = f"qbank_restore_{secrets.token_hex(6)}"
    yield name
    drop_database(name)


# What a restore must reproduce, each as one query (read as a superuser, so no row is filtered).
_QUERIES: dict[str, str] = {
    "revision": "SELECT version_num FROM alembic_version",
    "columns": """
        SELECT table_name, column_name, data_type, is_nullable, column_default
        FROM information_schema.columns WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position""",
    "indexes": """
        SELECT tablename, indexname, indexdef FROM pg_indexes
        WHERE schemaname = 'public' ORDER BY 1, 2""",
    "constraints": """
        SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) FROM pg_constraint
        WHERE connamespace = 'public'::regnamespace ORDER BY 1, 2""",
    "functions": """
        SELECT proname, prosecdef, pg_get_function_identity_arguments(oid) FROM pg_proc
        WHERE pronamespace = 'public'::regnamespace ORDER BY 1, 3""",
    "row_security": """
        SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class
        WHERE relnamespace = 'public'::regnamespace AND relkind = 'r' ORDER BY 1""",
    "policies": """
        SELECT tablename, policyname, permissive, roles::text, cmd, qual, with_check
        FROM pg_policies WHERE schemaname = 'public' ORDER BY 1, 2""",
    "table_grants": """
        SELECT table_name, grantee, privilege_type FROM information_schema.role_table_grants
        WHERE table_schema = 'public' AND grantee = ANY(%(roles)s) ORDER BY 1, 2, 3""",
    "routine_grants": """
        SELECT routine_name, grantee, privilege_type FROM information_schema.routine_privileges
        WHERE routine_schema = 'public' AND grantee = ANY(%(roles)s) ORDER BY 1, 2, 3""",
}


def _snapshot(database: str) -> dict[str, object]:
    """Everything about a database that a restore must reproduce."""
    url = make_url(ADMIN_URL).set(drivername="postgresql", database=database)
    with psycopg.connect(url.render_as_string(hide_password=False)) as conn:
        is_superuser = conn.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")
        assert is_superuser.fetchone() == (True,), (
            "The drill must read both databases as a superuser, or row counts would be filtered."
        )
        snapshot: dict[str, object] = {
            name: conn.execute(query, {"roles": [APP_ROLE, WORKER_ROLE]}).fetchall()
            for name, query in _QUERIES.items()
        }
        tables = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        counts: dict[str, int] = {}
        for (table,) in sorted(tables.fetchall()):
            count = sql.SQL("SELECT count(*) FROM public.{}").format(sql.Identifier(table))
            counts[table] = conn.execute(count).fetchone()[0]  # type: ignore[index]
        snapshot["counts"] = counts
        return snapshot


def test_restored_copy_matches_and_keeps_tenant_isolation(
    migrated_database: MigratedDatabase,
    backup: Path,
    restored_name: str,
    coaching_a: Coaching,
    coaching_b: Coaching,
    tmp_path: Path,
) -> None:
    # Taken after the two coachings exist, so there is tenant data to lose.
    fresh = tmp_path / "fresh.dump"
    result = _run("backup-db.sh", fresh, env=_connection_env(migrated_database.name))
    assert result.returncode == 0, result.stderr
    result = _run("restore-db.sh", fresh, restored_name, env=_connection_env("postgres"))
    assert result.returncode == 0, result.stderr

    original = _snapshot(migrated_database.name)
    restored = _snapshot(restored_name)

    # The comparison must not be vacuous.
    counts = original["counts"]
    assert isinstance(counts, dict) and counts["organizations"] >= 2
    assert any(forced for _, _, forced in original["row_security"])  # type: ignore[attr-defined]
    assert original["policies"] and original["table_grants"] and original["routine_grants"]

    for part in original:
        assert restored[part] == original[part], f"The restored database differs in: {part}"

    # Behaviour, as the runtime role: each coaching sees only its own rows, no context sees none.
    app_url = make_url(migrated_database.app_url).set(database=restored_name)
    database = Database(app_url.render_as_string(hide_password=False))
    try:
        with database.transaction(coaching_a.context) as session:
            assert set(session.scalars(select(Organization.id))) == {coaching_a.org_id}
        with database.transaction(coaching_b.context) as session:
            assert set(session.scalars(select(Organization.id))) == {coaching_b.org_id}
        with database.transaction(NO_CONTEXT) as session:
            assert set(session.scalars(select(Organization.id))) == set()
    finally:
        database.dispose()


def test_backup_refuses_a_role_that_cannot_bypass_row_security(
    migrated_database: MigratedDatabase, tmp_path: Path
) -> None:
    target = tmp_path / "never.dump"
    env = _connection_env(migrated_database.name, user=APP_ROLE, password=APP_PASSWORD)
    result = _run("backup-db.sh", target, env=env)

    assert result.returncode != 0
    assert "cannot bypass row-level security" in result.stderr
    assert not target.exists() and not Path(f"{target}.partial").exists()


def test_restore_never_overwrites_an_existing_database(
    migrated_database: MigratedDatabase, backup: Path
) -> None:
    result = _run("restore-db.sh", backup, migrated_database.name, env=_connection_env("postgres"))

    assert result.returncode != 0
    assert "already exists" in result.stderr


def test_restore_refuses_a_damaged_backup(backup: Path, tmp_path: Path, restored_name: str) -> None:
    damaged = tmp_path / "damaged.dump"
    shutil.copy(backup, damaged)
    shutil.copy(f"{backup}.sha256", f"{damaged}.sha256")
    (tmp_path / "damaged.dump.sha256").write_text(
        (tmp_path / "damaged.dump.sha256").read_text().replace("drill.dump", "damaged.dump")
    )
    with damaged.open("ab") as file:
        file.write(b"x")

    result = _run("restore-db.sh", damaged, restored_name, env=_connection_env("postgres"))

    assert result.returncode != 0
    assert "checksum" in result.stderr
    with psycopg.connect(
        make_url(ADMIN_URL).set(drivername="postgresql").render_as_string(hide_password=False)
    ) as conn:
        found = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (restored_name,)
        ).fetchone()
    assert found is None  # nothing was created


# Two ways a backup can name a role besides qbank_app and qbank_worker: a plain GRANT to it, and
# default privileges set FOR it. Each scenario: SQL that makes the backup name the role, SQL that
# undoes it so the role can be dropped, and a check on the restored database ({role} is filled in).
_ROLE_SCENARIOS = {
    "grant": (
        "GRANT SELECT ON organizations TO {role}",
        "REVOKE SELECT ON organizations FROM {role}",
        "SELECT has_table_privilege('{role}', 'organizations', 'SELECT')",
    ),
    "default_privileges_for_role": (
        "ALTER DEFAULT PRIVILEGES FOR ROLE {role} IN SCHEMA public "
        "GRANT SELECT ON TABLES TO qbank_app",
        "ALTER DEFAULT PRIVILEGES FOR ROLE {role} IN SCHEMA public "
        "REVOKE SELECT ON TABLES FROM qbank_app",
        "SELECT EXISTS (SELECT 1 FROM pg_default_acl d JOIN pg_roles r ON r.oid = d.defaclrole "
        "WHERE r.rolname = '{role}')",
    ),
}


@pytest.mark.parametrize("scenario", list(_ROLE_SCENARIOS))
def test_restore_stops_before_starting_when_a_named_role_is_missing(
    scenario: str, migrated_database: MigratedDatabase, tmp_path: Path
) -> None:
    """A backup keeps every GRANT and default privilege. On a server without a role it names, the
    restore must stop with a clear message and create nothing; once the role exists, the same file
    restores and keeps what it granted."""
    make, undo, check = _ROLE_SCENARIOS[scenario]
    role = f"qbank_extra_{secrets.token_hex(4)}"
    target = f"qbank_restore_{secrets.token_hex(6)}"
    admin = make_url(ADMIN_URL).set(drivername="postgresql")
    source = admin.set(database=migrated_database.name).render_as_string(hide_password=False)
    server = admin.render_as_string(hide_password=False)
    dump = tmp_path / "extra.dump"

    def run_sql(url: str, statement: str) -> None:
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute(statement.format(role=sql.Identifier(role).as_string(conn)))  # type: ignore[arg-type]

    try:
        run_sql(server, "CREATE ROLE {role}")
        run_sql(source, make)
        result = _run("backup-db.sh", dump, env=_connection_env(migrated_database.name))
        assert result.returncode == 0, result.stderr
        # A server that has never heard of the role: undo it in the source, then drop the role.
        run_sql(source, undo)
        run_sql(server, "DROP ROLE {role}")

        result = _run("restore-db.sh", dump, target, env=_connection_env("postgres"))
        assert result.returncode != 0
        assert role in result.stderr and "do not exist" in result.stderr
        with psycopg.connect(server) as conn:
            found = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (target,)
            ).fetchone()
        assert found is None  # it stopped before creating anything

        run_sql(server, "CREATE ROLE {role}")
        result = _run("restore-db.sh", dump, target, env=_connection_env("postgres"))
        assert result.returncode == 0, result.stderr
        restored = admin.set(database=target).render_as_string(hide_password=False)
        with psycopg.connect(restored) as conn:
            assert conn.execute(check.format(role=role)).fetchone() == (True,)  # type: ignore[arg-type]
    finally:
        drop_database(target)
        with psycopg.connect(server, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role)))
