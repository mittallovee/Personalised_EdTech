"""Identifier generation (ADR-0011)."""

import uuid


def new_id() -> uuid.UUID:
    """Return a new time-ordered UUIDv7 for a database row."""
    return uuid.uuid7()
