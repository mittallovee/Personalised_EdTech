"""A syllabus item with a parent must also say the parent's kind (M3 PR 2a, follow-up).

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-22

Migration 0013's CHECK on ``taxonomy_nodes`` lists the allowed (kind, parent kind) pairs. A CHECK
passes when it evaluates to NULL, and the composite foreign key to the parent is skipped when any
of its columns is NULL. So a row with a ``parent_id`` but no ``parent_kind`` got through both, and
could hang under a made-up parent. The new CHECK also requires ``parent_kind IS NOT NULL`` whenever
there is a parent, so it evaluates to true or false for every row.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE taxonomy_nodes DROP CONSTRAINT taxonomy_nodes_check;
        ALTER TABLE taxonomy_nodes ADD CONSTRAINT taxonomy_nodes_parent_pair CHECK (
            (kind = 'CLASS' AND parent_id IS NULL AND parent_kind IS NULL)
            OR (parent_id IS NOT NULL AND parent_kind IS NOT NULL AND (
                (kind = 'SUBJECT' AND parent_kind = 'CLASS')
                OR (kind = 'CHAPTER' AND parent_kind = 'SUBJECT')
                OR (kind = 'TOPIC' AND parent_kind = 'CHAPTER')
                OR (kind = 'SUBTOPIC' AND parent_kind = 'TOPIC')
            ))
        );
    """)


def downgrade() -> None:
    # Back to the check of 0013 (which accepts a parent with no parent kind).
    op.execute("""
        ALTER TABLE taxonomy_nodes DROP CONSTRAINT taxonomy_nodes_parent_pair;
        ALTER TABLE taxonomy_nodes ADD CONSTRAINT taxonomy_nodes_check CHECK (
            (kind = 'CLASS' AND parent_id IS NULL AND parent_kind IS NULL)
            OR (parent_id IS NOT NULL AND (
                (kind = 'SUBJECT' AND parent_kind = 'CLASS')
                OR (kind = 'CHAPTER' AND parent_kind = 'SUBJECT')
                OR (kind = 'TOPIC' AND parent_kind = 'CHAPTER')
                OR (kind = 'SUBTOPIC' AND parent_kind = 'TOPIC')
            ))
        );
    """)
