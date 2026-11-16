"""The bank index: one derived row per question, for fast lists, filters and counts (M4 PR 4e).

Revision ID: 0029
Revises: 0028
Create Date: 2026-11-16

M4 design note §7.1, ADR-0008 (F-01, F-02): the question content lives in JSON inside revisions,
which cannot be filtered or counted quickly over a lakh of questions. ``bank_index`` holds one row
per master with the labels pulled out into columns. It is derived data: the questions module writes
it in the same transaction as every change, and ``qbank reindex-bank`` rebuilds it from the
revisions, so nothing here is ever the only copy of anything.

The row shows the *bank version*: the published version if there is one (a question being
corrected still reads as published to everyone else), else the newest. ``is_private`` is true when
that version is work in progress (a draft or a returned question), which only its author, admins
and edit-others holders may read; the list applies it in the query so a private question can never
leak through a list or a count.

Free text, trigram and duplicate columns come with the PRs that use them (4f, 4g); the indexes
here are the starting set and are chosen from measurements in 4f.

Coaching-owned, so FORCE row-level security with the tenant policy and a composite foreign key.
Rows are written and changed by the app role and never deleted (a question is archived, not
removed).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE bank_index (
            organization_id     uuid NOT NULL REFERENCES organizations (id),
            master_id           uuid NOT NULL,
            code                text NOT NULL,
            created_by          uuid NOT NULL REFERENCES users (id),
            created_at          timestamptz NOT NULL,
            updated_at          timestamptz NOT NULL,

            version_number      integer NOT NULL CHECK (version_number >= 1),
            state               text NOT NULL,
            is_private          boolean NOT NULL,
            is_archived         boolean NOT NULL,
            has_published       boolean NOT NULL,
            has_open_correction boolean NOT NULL,

            question_type       text,
            language            text,
            class_id            uuid,
            subject_id          uuid,
            chapter_id          uuid,
            topic_id            uuid,
            primary_concept_id  uuid,
            concept_ids         uuid[] NOT NULL DEFAULT '{}',
            difficulty          smallint CHECK (difficulty BETWEEN 1 AND 10),
            bloom_level         text,
            is_pyq              boolean NOT NULL,
            exam_id             uuid,
            exam_year           smallint,
            has_solution        boolean NOT NULL,
            has_video           boolean NOT NULL,

            PRIMARY KEY (organization_id, master_id),
            FOREIGN KEY (organization_id, master_id)
                REFERENCES question_masters (organization_id, id)
        );

        CREATE UNIQUE INDEX bank_index_code ON bank_index (organization_id, code);
        -- The default order of the list: the most recently changed first.
        CREATE INDEX bank_index_listing
            ON bank_index (organization_id, updated_at DESC, master_id DESC);
        CREATE INDEX bank_index_syllabus
            ON bank_index (organization_id, subject_id, chapter_id, topic_id);
        CREATE INDEX bank_index_concepts ON bank_index USING gin (concept_ids);

        ALTER TABLE bank_index ENABLE ROW LEVEL SECURITY;
        ALTER TABLE bank_index FORCE ROW LEVEL SECURITY;
        CREATE POLICY bank_index_tenant ON bank_index FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON bank_index TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP TABLE bank_index;")
