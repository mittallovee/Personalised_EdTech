"""The runtime role's limited access to login data (migration 0002)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.tenancy import TenantContext

AUTH_FUNCTIONS = (
    "auth_find_login(text)",
    "auth_register_login_failure(uuid, integer, interval)",
    "auth_register_login_success(uuid)",
    "auth_find_session(text)",
)


def test_runtime_role_cannot_read_password_hashes(db: Database) -> None:
    with pytest.raises(DBAPIError, match="permission denied"), db.engine.begin() as conn:
        conn.execute(text("SELECT * FROM password_credentials"))


@pytest.mark.parametrize("function", AUTH_FUNCTIONS)
def test_login_functions_are_not_public(db: Database, function: str) -> None:
    with db.engine.connect() as conn:
        public_can = conn.execute(
            text("SELECT has_function_privilege('public', :f, 'EXECUTE')"), {"f": function}
        ).scalar()
        app_can = conn.execute(
            text("SELECT has_function_privilege('qbank_app', :f, 'EXECUTE')"), {"f": function}
        ).scalar()

    assert public_can is False
    assert app_can is True


def test_runtime_role_cannot_create_sessions_for_someone_else(db: Database) -> None:
    signed_in, someone_else = new_id(), new_id()
    with (
        pytest.raises(DBAPIError, match="row-level security"),
        db.transaction(TenantContext(user_id=signed_in)) as session,
    ):
        session.execute(
            text(
                "INSERT INTO sessions (id, user_id, token_hash, csrf_token_hash, idle_expires_at,"
                " absolute_expires_at) VALUES (:id, :user, 'x', 'y', now(), now())"
            ),
            {"id": new_id(), "user": someone_else},
        )
