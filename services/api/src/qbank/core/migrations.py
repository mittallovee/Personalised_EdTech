"""Helpers to compare the database schema version with the code's migrations."""

from pathlib import Path

from alembic.script import ScriptDirectory


def migration_heads(migrations_dir: Path) -> frozenset[str]:
    """Return the latest migration revision(s) shipped with this code."""
    return frozenset(ScriptDirectory(str(migrations_dir)).get_heads())
