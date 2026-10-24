"""Retention of syllabus import previews that were never applied (K-10b, ADR-0018).

Revision ID: 0018
Revises: 0017
Create Date: 2026-10-24

A preview stores every checked row (6 to 8 MB for the largest file) and used to be kept forever.
Now an unapplied preview is kept while it is among the newest few of its coaching and recent;
after that its stored rows are dropped and it becomes ``EXPIRED`` (a small record is left: who,
when, the file name and checksum, the counts). An applied preview keeps its rows: they are the
record of what was imported.

The runtime role still cannot delete a preview or rewrite its rows. The only way to expire one is
``catalogue_imports_expire``: a SECURITY DEFINER function that touches only ``PREVIEWED`` rows of
the caller's own coaching (``app_current_org()``, never an argument a client could choose), and
only ever turns them into ``EXPIRED`` with no rows. Row-level security still applies inside it
(FORCE), as a second guard.

Downgrade removes the expired records (their rows are already gone) before restoring the old rule.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"


def upgrade() -> None:
    op.execute("""
        ALTER TABLE catalogue_imports DROP CONSTRAINT catalogue_imports_state_check;
        ALTER TABLE catalogue_imports ADD CONSTRAINT catalogue_imports_state_check
            CHECK (state IN ('PREVIEWED', 'APPLIED', 'EXPIRED'));
    """)
    op.execute("""
        -- Expire the caller's unapplied previews that are older than keep_days or beyond the
        -- newest keep_count. Returns how many were expired.
        CREATE FUNCTION catalogue_imports_expire(keep_days integer, keep_count integer)
        RETURNS integer
        LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog, public AS $$
            WITH ranked AS (
                SELECT id, created_at,
                       row_number() OVER (ORDER BY created_at DESC, id DESC) AS position
                FROM public.catalogue_imports
                WHERE organization_id = public.app_current_org() AND state = 'PREVIEWED'
            ), expired AS (
                UPDATE public.catalogue_imports AS c
                SET state = 'EXPIRED', rows = '[]'::jsonb
                FROM ranked AS r
                WHERE c.id = r.id
                  AND c.organization_id = public.app_current_org()
                  AND c.state = 'PREVIEWED'  -- checked again: it may have been applied meanwhile
                  AND (r.position > keep_count
                       OR r.created_at < now() - make_interval(days => keep_days))
                RETURNING 1
            )
            SELECT count(*)::integer FROM expired
        $$;
    """)
    op.execute(f"""
        REVOKE ALL ON FUNCTION catalogue_imports_expire(integer, integer) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION catalogue_imports_expire(integer, integer) TO {APP_ROLE};
    """)


def downgrade() -> None:
    op.execute("""
        DROP FUNCTION catalogue_imports_expire(integer, integer);
        DELETE FROM catalogue_imports WHERE state = 'EXPIRED';
        ALTER TABLE catalogue_imports DROP CONSTRAINT catalogue_imports_state_check;
        ALTER TABLE catalogue_imports ADD CONSTRAINT catalogue_imports_state_check
            CHECK (state IN ('PREVIEWED', 'APPLIED'));
    """)
