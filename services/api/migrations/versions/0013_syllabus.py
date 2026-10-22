"""The syllabus tree: classes, subjects, chapters, topics and subtopics (M3 PR 2a).

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-22

M3 design note §4.1:
- ``taxonomy_nodes``: one table for the five kinds. Each kind (except CLASS) hangs under a parent of
  the next kind up. The database enforces it: the parent is referenced together with its kind, and
  a CHECK lists the allowed (kind, parent kind) pairs, so a topic can never sit under a class.
  (The CHECK names ``parent_id IS NOT NULL`` itself: a NULL inside a CHECK counts as passing.)
- Coaching-owned, so FORCE row-level security with the tenant policy, and every reference carries
  ``organization_id`` so a node can never point at another coaching's parent (ADR-0005).
- ``name`` is the English label; ``name_key`` is it normalised (case, spacing, Unicode form), and
  two siblings can never share one. Other languages live in ``taxonomy_labels``.
- Nodes are never deleted, only deprecated, so a question that refers to one still resolves (C-04).
  The runtime role therefore has no DELETE on ``taxonomy_nodes``.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE taxonomy_nodes (
            id              uuid PRIMARY KEY,
            organization_id uuid NOT NULL REFERENCES organizations (id),
            kind            text NOT NULL CHECK
                                (kind IN ('CLASS', 'SUBJECT', 'CHAPTER', 'TOPIC', 'SUBTOPIC')),
            parent_id       uuid,
            parent_kind     text,
            name            text NOT NULL CHECK (length(name) BETWEEN 1 AND 200),
            name_key        text NOT NULL CHECK (length(name_key) BETWEEN 1 AND 400),
            state           text NOT NULL DEFAULT 'ACTIVE'
                                CHECK (state IN ('ACTIVE', 'DEPRECATED')),
            sort_order      integer NOT NULL DEFAULT 0,
            revision        integer NOT NULL DEFAULT 1,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (organization_id, id),
            UNIQUE (organization_id, id, kind),
            FOREIGN KEY (organization_id, parent_id, parent_kind)
                REFERENCES taxonomy_nodes (organization_id, id, kind),
            CHECK (
                (kind = 'CLASS' AND parent_id IS NULL AND parent_kind IS NULL)
                OR (parent_id IS NOT NULL AND (
                    (kind = 'SUBJECT' AND parent_kind = 'CLASS')
                    OR (kind = 'CHAPTER' AND parent_kind = 'SUBJECT')
                    OR (kind = 'TOPIC' AND parent_kind = 'CHAPTER')
                    OR (kind = 'SUBTOPIC' AND parent_kind = 'TOPIC')
                ))
            )
        );
        -- Siblings (same parent, or all classes) have different names. Used by the lookups of the
        -- syllabus import too, which find a node by its path of names.
        CREATE UNIQUE INDEX taxonomy_nodes_sibling_name
            ON taxonomy_nodes (organization_id,
                               COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid),
                               name_key);
        -- The picker lists the children of one parent in the admin's order.
        CREATE INDEX taxonomy_nodes_children
            ON taxonomy_nodes (organization_id, parent_id, sort_order, name_key, id);

        CREATE TABLE taxonomy_labels (
            organization_id uuid NOT NULL,
            node_id         uuid NOT NULL,
            language        text NOT NULL CHECK (language ~ '^[a-z]{2,3}$'),
            label           text NOT NULL CHECK (length(label) BETWEEN 1 AND 200),
            PRIMARY KEY (node_id, language),
            FOREIGN KEY (organization_id, node_id)
                REFERENCES taxonomy_nodes (organization_id, id)
        );
        CREATE INDEX taxonomy_labels_org ON taxonomy_labels (organization_id);

        ALTER TABLE taxonomy_nodes ENABLE ROW LEVEL SECURITY;
        ALTER TABLE taxonomy_nodes FORCE ROW LEVEL SECURITY;
        CREATE POLICY taxonomy_nodes_tenant ON taxonomy_nodes FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());

        ALTER TABLE taxonomy_labels ENABLE ROW LEVEL SECURITY;
        ALTER TABLE taxonomy_labels FORCE ROW LEVEL SECURITY;
        CREATE POLICY taxonomy_labels_tenant ON taxonomy_labels FOR ALL
            USING (organization_id = app_current_org())
            WITH CHECK (organization_id = app_current_org());
    """)
    op.execute(f"""
        GRANT SELECT, INSERT, UPDATE ON taxonomy_nodes TO {APP_ROLE};   -- retire, never delete
        GRANT SELECT, INSERT, UPDATE, DELETE ON taxonomy_labels TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE taxonomy_labels;
        DROP TABLE taxonomy_nodes;
    """)
