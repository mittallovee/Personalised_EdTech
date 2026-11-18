"""What the duplicate check compares, on the bank index (M4 PR 4g-1, D-16).

Revision ID: 0032
Revises: 0031
Create Date: 2026-11-17

M4 design note §7.4. ``bank_index`` gains:

- ``duplicate_key``: a hash of the question's meaning (format, stem, options, answer; prose without
  case or spacing differences, equations as written). Two rows with the same key are exact
  duplicates. Indexed with the coaching, so the exact check is one index lookup.
- ``match_text``: the question's text without the worked solution (the same question with another
  solution is still the same question), with a trigram index for the near check.

The trigram index on the whole text (``bank_index_stem_trgm``, migration 0030) is dropped: since
0031 search matches typos through the word list, so nothing reads it any more, and keeping it would
cost every save. Existing rows get their key and text when ``qbank reindex-bank`` runs (the release
note says so); until then they are simply not found as duplicates.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE bank_index
            ADD COLUMN duplicate_key text CHECK (length(duplicate_key) = 64),
            ADD COLUMN match_text text NOT NULL DEFAULT '';
        CREATE INDEX bank_index_duplicate_key ON bank_index (organization_id, duplicate_key)
            WHERE duplicate_key IS NOT NULL;
        CREATE INDEX bank_index_match_trgm ON bank_index USING gin (match_text gin_trgm_ops);
        DROP INDEX bank_index_stem_trgm;
    """)


def downgrade() -> None:
    op.execute("""
        CREATE INDEX bank_index_stem_trgm ON bank_index USING gin (stem_text gin_trgm_ops);
        DROP INDEX bank_index_match_trgm;
        DROP INDEX bank_index_duplicate_key;
        ALTER TABLE bank_index DROP COLUMN match_text, DROP COLUMN duplicate_key;
    """)
