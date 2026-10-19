import pytest
from pydantic import ValidationError

from qbank.core.config import AppEnv, Settings
from qbank.core.security import (
    hash_password,
    hash_token,
    new_token,
    password_needs_rehash,
    token_matches,
    verify_password,
)


def test_password_hash_verifies_only_the_right_password() -> None:
    stored = hash_password("correct horse battery")

    assert stored.startswith("$argon2id$")
    assert verify_password(stored, "correct horse battery")
    assert not verify_password(stored, "wrong password")
    assert not password_needs_rehash(stored)


def test_missing_hash_never_verifies() -> None:
    assert not verify_password(None, "anything")


def test_tokens_are_random_and_stored_as_hashes() -> None:
    token = new_token()

    assert token != new_token()
    assert len(token) >= 43
    assert hash_token(token) != token
    assert token_matches(token, hash_token(token))
    assert not token_matches(new_token(), hash_token(token))


def test_production_refuses_insecure_cookies() -> None:
    with pytest.raises(ValidationError, match="SESSION_COOKIE_SECURE"):
        Settings(app_env=AppEnv.PRODUCTION, database_url="x", session_cookie_secure=False)
