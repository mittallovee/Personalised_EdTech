"""Permanent 8-character public codes, e.g. ``7K2M9PQX`` (ADR-0011, D-11).

Alphabet: Crockford Base32 (digits and capital letters without I, L, O, U), so codes are easy to
read aloud and print. Typed input is forgiving: lower case is accepted, O reads as 0, I/L as 1.
Codes are random, globally unique across coachings and never reused.
"""

import secrets
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from qbank.core.errors import ValidationFailed

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 8
MAX_ATTEMPTS = 5  # 32^8 ≈ 1.1 trillion codes, so even one retry is extremely rare

_TYPO_FIXES = str.maketrans({"O": "0", "I": "1", "L": "1"})

_RESERVE = text(
    "INSERT INTO public_codes (code, entity_type, organization_id)"
    " VALUES (:code, :entity_type, :organization_id)"
    " ON CONFLICT (code) DO NOTHING"
)


def generate_code() -> str:
    """A random code from a cryptographically secure source."""
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(typed: str) -> str:
    """Turn what a person typed into the canonical code, or raise ``ValidationFailed``."""
    code = typed.strip().replace("-", "").replace(" ", "").upper().translate(_TYPO_FIXES)
    if len(code) != CODE_LENGTH or any(ch not in ALPHABET for ch in code):
        raise ValidationFailed(f"'{typed}' is not a valid code.", code="INVALID_CODE")
    return code


def reserve_code(session: Session, *, entity_type: str, organization_id: UUID) -> str:
    """Issue a new unique code inside the caller's transaction, retrying on the rare collision.

    The primary key on ``public_codes`` checks uniqueness across all coachings, even though
    row-level security only lets each coaching read its own codes.
    """
    for _ in range(MAX_ATTEMPTS):
        code = generate_code()
        inserted = session.execute(
            _RESERVE,
            {"code": code, "entity_type": entity_type, "organization_id": organization_id},
        )
        if inserted.rowcount == 1:  # type: ignore[attr-defined]
            return code
    raise RuntimeError("Could not allocate a unique code; check the code generator.")
