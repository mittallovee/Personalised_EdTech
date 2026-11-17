"""Free-text and typo search on the bank index (M4 PR 4f).

Revision ID: 0030
Revises: 0029
Create Date: 2026-11-17

M4 design note §7.3, ADR-0008 (F-03). ``bank_index`` gains the plain text of each question
(``stem_text``: stem, options, solution; equations as the LaTeX written), its beginning for the list
(``preview``), and a word index of the text (``search_vector``), which PostgreSQL keeps in step by
itself (a generated column), so no writer can forget it.

- Words are searched with the ``simple`` text-search configuration: no stemmer exists for the Indian
  languages, and it still matches whole words in Hindi, Gujarati and the rest.
- Typos are found with trigram similarity (the ``pg_trgm`` extension, one of PostgreSQL's standard
  ones and "trusted", so the table owner may create it). Both indexes are GIN.

The two indexes are the starting set; the 100,000-question measurements (K-08) say whether they
stay. Existing rows have empty text until ``qbank reindex-bank`` runs once (the release note says
so).
The downgrade drops the columns and indexes and leaves the extension installed: other things may use
it, and it does nothing on its own.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        ALTER TABLE bank_index
            ADD COLUMN stem_text text NOT NULL DEFAULT '',
            ADD COLUMN preview text NOT NULL DEFAULT '',
            ADD COLUMN search_vector tsvector
                GENERATED ALWAYS AS (to_tsvector('simple', stem_text)) STORED
        """
    )
    op.execute("CREATE INDEX bank_index_search_vector ON bank_index USING gin (search_vector)")
    op.execute("CREATE INDEX bank_index_stem_trgm ON bank_index USING gin (stem_text gin_trgm_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS bank_index_stem_trgm")
    op.execute("DROP INDEX IF EXISTS bank_index_search_vector")
    op.execute(
        "ALTER TABLE bank_index DROP COLUMN search_vector, DROP COLUMN preview,"
        " DROP COLUMN stem_text"
    )
