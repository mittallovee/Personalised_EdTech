"""The pages of an uploaded document (M6 6c, G-03, G-04).

Revision ID: 0045
Revises: 0044
Create Date: 2026-11-28

M6 design note §5. The sandboxed worker turns an original into pages: a picture (JPEG,
re-encoded, so nothing hidden in the original survives), a small thumbnail, the text the document
itself carries (selectable PDF text, the paragraphs of a Word file), and for a Word file the
pictures embedded in it. A page is written once and never changed: what the AI reads later is
always inspectable. A page that could not be read is kept as a row with ``state = 'FAILED'`` and a
code, so a partial file stays partial and says why.

- ``(file_id, page_no)`` is unique, so a retried render cannot make a page twice.
- The sandbox role may read and add pages of the job's own coaching (row-level security applies to
  it too) and nothing else; the API role may only read them.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0045"
down_revision: str | None = "0044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"
INGEST_ROLE = "qbank_ingest"


def upgrade() -> None:
    op.execute(f"""
        CREATE TABLE ingest_pages (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL,
            file_id         uuid NOT NULL,
            page_no         integer NOT NULL CHECK (page_no >= 1),
            state           text NOT NULL CHECK (state IN ('READY', 'FAILED')),
            image_key       text,
            thumb_key       text,
            width           integer CHECK (width IS NULL OR width > 0),
            height          integer CHECK (height IS NULL OR height > 0),
            text            text CHECK (text IS NULL OR char_length(text) <= 200000),
            figures         jsonb NOT NULL DEFAULT '[]'::jsonb,
            warnings        jsonb NOT NULL DEFAULT '[]'::jsonb,
            error_code      text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            FOREIGN KEY (organization_id, file_id)
                REFERENCES ingest_files (organization_id, id),
            UNIQUE (file_id, page_no),
            UNIQUE (organization_id, id)
        );
        ALTER TABLE ingest_pages ENABLE ROW LEVEL SECURITY;
        ALTER TABLE ingest_pages FORCE ROW LEVEL SECURITY;
        CREATE POLICY ingest_pages_tenant ON ingest_pages FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());

        GRANT SELECT ON ingest_pages TO {APP_ROLE};
        GRANT SELECT, INSERT ON ingest_pages TO {INGEST_ROLE};
    """)


def downgrade() -> None:
    op.execute("DROP TABLE ingest_pages;")
