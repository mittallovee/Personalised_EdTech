"""Password hashing and random tokens (standards §5: Argon2id, hashed session tokens)."""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# argon2-cffi defaults follow RFC 9106 (Argon2id). Parameters are stored inside each hash, so they
# can be raised later; ``needs_rehash`` then tells us to upgrade a hash at the next login.
_hasher = PasswordHasher()

# Verified against when an email is unknown, so "no such user" takes as long as "wrong password".
_TIMING_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Check a password; with ``password_hash=None`` do equal work and return False."""
    try:
        matched = _hasher.verify(password_hash or _TIMING_DUMMY_HASH, password)
    except VerificationError, InvalidHashError:
        return False
    return matched and password_hash is not None


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_token() -> str:
    """A URL-safe random token with 256 bits of entropy (session cookies, CSRF tokens)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Tokens are stored only as SHA-256 hashes, so a database leak does not leak live sessions."""
    return hashlib.sha256(token.encode()).hexdigest()


def token_matches(token: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), expected_hash)
