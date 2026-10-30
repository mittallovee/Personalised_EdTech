"""Remember the trace a background job belongs to (K-06c, ADR-0019).

Revision ID: 0019
Revises: 0018
Create Date: 2026-10-30

A job is enqueued by a request and run later by the worker. ``traceparent`` (the W3C Trace Context
header: version, trace ID, span ID, flags) is stored with the job so the worker's span continues
the request's trace, and one search shows the request, its SQL and the job together. It holds only
those identifiers. NULL for jobs enqueued while tracing is off, and for jobs that already exist.

Nothing else changes: ``jobs_claim`` returns whole ``jobs`` rows, so it hands the new column to the
worker without being redefined; the runtime role's table-level INSERT privilege already covers it.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE jobs ADD COLUMN traceparent text")


def downgrade() -> None:
    op.execute("ALTER TABLE jobs DROP COLUMN traceparent")
