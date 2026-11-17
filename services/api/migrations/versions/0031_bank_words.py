"""The words of each coaching's bank, for fast typo search (M4 PR 4f-2, K-08).

Revision ID: 0031
Revises: 0030
Create Date: 2026-11-17

The 100,000-question measurements (docs/operations/load-tests.md) showed that matching a typo
against the whole text of every question takes about 4 seconds: the trigram index finds tens of
thousands of candidates and each must be compared. A typo is a misspelt *word*, so it is matched
against the coaching's list of distinct words instead (a few thousand, even for a big bank), and
the close words are then searched with the word index like any other search. This is the pattern
the PostgreSQL documentation gives for spelling suggestions.

``bank_words`` holds each distinct word (3 to 40 characters) of a coaching's ``bank_index`` text.
A trigger on ``bank_index`` adds the words of every row written, so no writer can forget it; the
rows already there are added here. Words are never removed: a word that no longer appears only
widens a typo search to a word that finds nothing. It is derived data like ``bank_index``.

Coaching-owned: FORCE row-level security with the tenant policy, so one coaching's words are never
used for another's search. The word list only ever picks words to search for; which questions come
back is decided by the bank's visibility rule, as for every search.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE bank_words (
            organization_id uuid NOT NULL REFERENCES organizations (id),
            word            text NOT NULL CHECK (length(word) BETWEEN 3 AND 40),
            PRIMARY KEY (organization_id, word)
        );
        CREATE INDEX bank_words_trgm ON bank_words USING gin (word gin_trgm_ops);

        ALTER TABLE bank_words ENABLE ROW LEVEL SECURITY;
        ALTER TABLE bank_words FORCE ROW LEVEL SECURITY;
        CREATE POLICY bank_words_tenant ON bank_words FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());

        CREATE FUNCTION bank_index_words() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            INSERT INTO bank_words (organization_id, word)
                SELECT NEW.organization_id, lexeme FROM unnest(NEW.search_vector)
                WHERE length(lexeme) BETWEEN 3 AND 40
                ON CONFLICT DO NOTHING;
            RETURN NULL;
        END;
        $$;
        CREATE TRIGGER bank_index_words
            AFTER INSERT OR UPDATE OF stem_text ON bank_index
            FOR EACH ROW EXECUTE FUNCTION bank_index_words();

        INSERT INTO bank_words (organization_id, word)
            SELECT DISTINCT organization_id, lexeme FROM bank_index, unnest(search_vector)
            WHERE length(lexeme) BETWEEN 3 AND 40
            ON CONFLICT DO NOTHING;
    """)
    op.execute(f"GRANT SELECT, INSERT ON bank_words TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER bank_index_words ON bank_index;
        DROP FUNCTION bank_index_words();
        DROP TABLE bank_words;
    """)
