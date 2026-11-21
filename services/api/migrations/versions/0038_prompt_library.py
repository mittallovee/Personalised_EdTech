"""The prompt library: platform, coaching and personal prompts, immutable versions (M5 5d-1).

Revision ID: 0038
Revises: 0037
Create Date: 2026-11-21

M5 design note §10 and the prompt spec (PL-01 to PL-11).

- ``prompt_templates``: one row per prompt a person can pick, at one of three levels: ``PLATFORM``
  (ours, one per operation, no coaching), ``COACHING`` (a coaching's own version of an operation,
  optionally for one target language) and ``PERSONAL`` (one author's own). ``active_version_id``
  is the version in use (platform and coaching levels); a coaching template with none follows the
  platform default. ``based_on_version_id`` is the platform version a coaching prompt was last
  derived from or acknowledged, so a newer platform version shows as "new default available".
- ``prompt_versions``: the instructions text, saved once and never changed (a trigger refuses
  UPDATE and DELETE even for the table owner). ``content_hash`` fingerprints the text and settings.
- ``prompt_activations``: append-only history of every switch (activate, rollback, reset,
  adopting a newer platform default).

The locked parts of a prompt (the safety preamble, the output format, the list of placeholders) are
code, not data, so a prompt edit cannot loosen them. Four platform default prompts are seeded here.

Platform rows have no ``organization_id``: everyone can read them, only a platform admin can add
them. Coaching rows are visible to that coaching only (FORCE row-level security); a personal
prompt is further limited to its author and the admins by the service.
"""

import hashlib
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "qbank_app"
_NAMESPACE = uuid.UUID("6f1c2a9e-5b1d-4c53-9d1e-2f6a8b7c1d00")

_DEFAULTS: list[tuple[str, str, str, str | None]] = [
    (
        "TAG",
        "Tag a question",
        "You label a question for a coaching institute's question bank. Using only the syllabus"
        " below, choose the chapter, topic and concepts the question belongs to, estimate its"
        " difficulty from 1 (very easy) to 10 (very hard) for a well-prepared student, and give its"
        " Bloom level. Use only ids that appear in the syllabus list and never invent one. If"
        " nothing fits, leave that field empty instead of guessing.\n\n"
        "Syllabus (id and name):\n{{syllabus}}\n\n"
        "Question:\n{{question}}",
        "0.2",
    ),
    (
        "TRANSLATE",
        "Translate a question",
        "Translate the question below from {{source_language}} into {{target_language}} for"
        " students preparing for competitive exams. Keep the meaning, the difficulty and every"
        " number, unit, symbol, chemical formula and LaTeX expression exactly as written; do not"
        " translate anything inside LaTeX. Keep the options in the same order with the same labels."
        " Use the standard textbook terms of the target language, and use the glossary entries"
        " below wherever the source term appears. Do not add explanations or hints.\n\n"
        "Glossary (source term = target term):\n{{glossary}}\n\n"
        "Question:\n{{question}}",
        "0.3",
    ),
    (
        "SOLVE",
        "Solve a question",
        "Solve the question below. Work step by step, check your arithmetic and units, then give"
        " the final answer in the form the question's format asks for (an option label, a number, a"
        " set of options, a matching and so on). Put a worked solution that a student could follow"
        " in the solution field. If the question is ambiguous or incomplete, say so in the solution"
        " instead of guessing.\n\n"
        "Format: {{format}}\n\n"
        "Question:\n{{question}}",
        "0.2",
    ),
    (
        "VERIFY",
        "Verify a question",
        "Check the question below as a careful subject teacher would. Is the stem complete and"
        " unambiguous? Is the keyed answer correct? Are the options distinct, with exactly as many"
        " correct ones as the format says? Is the worked solution right and consistent with the"
        " answer? Are units, signs and conventions right? Report each problem as a finding with the"
        " part of the question it concerns, a severity (error, warning or note) and a short"
        " message. Only if you are sure how to fix a problem, also give the corrected content."
        " Report nothing for what is fine.\n\n"
        "Question:\n{{question}}\n\n"
        "Answer:\n{{answer}}\n\n"
        "Solution:\n{{solution}}",
        "0.2",
    ),
]


def _hash(instructions: str, temperature: str | None) -> str:
    return hashlib.sha256(f"{instructions}\n{temperature or ''}".encode()).hexdigest()


def upgrade() -> None:
    op.execute("""
        CREATE TABLE prompt_templates (
            id                   uuid PRIMARY KEY,
            organization_id      uuid REFERENCES organizations (id),
            scope                text NOT NULL
                CHECK (scope IN ('PLATFORM', 'COACHING', 'PERSONAL')),
            operation            text NOT NULL
                CHECK (operation IN ('TAG', 'TRANSLATE', 'SOLVE', 'VERIFY')),
            owner_user_id        uuid REFERENCES users (id),
            name                 text NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
            target_language      text CHECK (target_language ~ '^[a-z]{2,3}$'),
            active_version_id    uuid,
            based_on_version_id  uuid,
            revision             integer NOT NULL DEFAULT 1,
            created_by           uuid REFERENCES users (id),
            created_at           timestamptz NOT NULL DEFAULT now(),
            updated_at           timestamptz NOT NULL DEFAULT now(),
            CHECK (
                (scope = 'PLATFORM' AND organization_id IS NULL AND owner_user_id IS NULL
                    AND target_language IS NULL)
                OR (scope = 'COACHING' AND organization_id IS NOT NULL AND owner_user_id IS NULL)
                OR (scope = 'PERSONAL' AND organization_id IS NOT NULL
                    AND owner_user_id IS NOT NULL)
            ),
            CHECK (target_language IS NULL OR operation = 'TRANSLATE')
        );
        CREATE UNIQUE INDEX prompt_templates_one_platform ON prompt_templates (operation)
            WHERE scope = 'PLATFORM';
        CREATE UNIQUE INDEX prompt_templates_one_coaching
            ON prompt_templates (organization_id, operation, coalesce(target_language, ''))
            WHERE scope = 'COACHING';
        CREATE UNIQUE INDEX prompt_templates_one_personal_name
            ON prompt_templates (organization_id, owner_user_id, operation, lower(name))
            WHERE scope = 'PERSONAL';

        CREATE TABLE prompt_versions (
            id              uuid PRIMARY KEY,
            organization_id uuid REFERENCES organizations (id),
            template_id     uuid NOT NULL REFERENCES prompt_templates (id),
            version_no      integer NOT NULL CHECK (version_no >= 1),
            instructions    text NOT NULL CHECK (length(instructions) BETWEEN 1 AND 8000),
            temperature     numeric(3, 2) CHECK (temperature >= 0 AND temperature <= 1),
            change_note     text NOT NULL CHECK (length(change_note) BETWEEN 1 AND 300),
            author_id       uuid REFERENCES users (id),
            content_hash    text NOT NULL CHECK (content_hash ~ '^[0-9a-f]{64}$'),
            created_at      timestamptz NOT NULL DEFAULT now(),
            UNIQUE (template_id, version_no),
            UNIQUE (template_id, id)
        );

        ALTER TABLE prompt_templates
            ADD FOREIGN KEY (id, active_version_id) REFERENCES prompt_versions (template_id, id),
            -- a platform version is on another template, so this one points at any version row
            ADD FOREIGN KEY (based_on_version_id) REFERENCES prompt_versions (id);

        CREATE TABLE prompt_activations (
            id              uuid PRIMARY KEY,
            organization_id uuid REFERENCES organizations (id),
            template_id     uuid NOT NULL REFERENCES prompt_templates (id),
            version_id      uuid REFERENCES prompt_versions (id),
            action          text NOT NULL
                CHECK (action IN ('ACTIVATE', 'ROLLBACK', 'RESET', 'ADOPT_DEFAULT')),
            activated_by    uuid REFERENCES users (id),
            activated_at    timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX prompt_activations_by_template
            ON prompt_activations (template_id, activated_at DESC);

        CREATE FUNCTION prompt_history_refuse_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only: add a row instead', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$;
        CREATE TRIGGER prompt_versions_no_change BEFORE UPDATE OR DELETE ON prompt_versions
            FOR EACH ROW EXECUTE FUNCTION prompt_history_refuse_change();
        CREATE TRIGGER prompt_activations_no_change BEFORE UPDATE OR DELETE ON prompt_activations
            FOR EACH ROW EXECUTE FUNCTION prompt_history_refuse_change();
    """)
    # Platform rows (no coaching) are readable by everyone and writable by a platform admin only;
    # coaching rows belong to that coaching alone.
    for table in ("prompt_templates", "prompt_versions", "prompt_activations"):
        op.execute(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
            CREATE POLICY {table}_read ON {table} FOR SELECT
                USING (organization_id IS NULL OR organization_id = app_current_org());
            CREATE POLICY {table}_add ON {table} FOR INSERT
                WITH CHECK (
                    (organization_id IS NULL AND app_is_platform())
                    OR organization_id = app_current_org()
                );
        """)
    op.execute("""
        CREATE POLICY prompt_templates_change ON prompt_templates FOR UPDATE
            USING ((organization_id IS NULL AND app_is_platform())
                   OR organization_id = app_current_org())
            WITH CHECK ((organization_id IS NULL AND app_is_platform())
                        OR organization_id = app_current_org());
    """)
    op.execute(f"""
        GRANT SELECT, INSERT, UPDATE ON prompt_templates TO {APP_ROLE};
        GRANT SELECT, INSERT ON prompt_versions, prompt_activations TO {APP_ROLE};
    """)

    # --- The platform's own default prompts (version 1 of each) ---------------------------------
    bind = op.get_bind()
    bind.execute(sa.text("SELECT set_config('app.is_platform', 'true', true)"))
    for operation, name, instructions, temperature in _DEFAULTS:
        template_id = uuid.uuid5(_NAMESPACE, f"template-{operation}")
        version_id = uuid.uuid5(_NAMESPACE, f"version-{operation}-1")
        bind.execute(
            sa.text(
                "INSERT INTO prompt_templates (id, scope, operation, name)"
                " VALUES (:id, 'PLATFORM', :operation, :name)"
            ),
            {"id": template_id, "operation": operation, "name": name},
        )
        bind.execute(
            sa.text(
                "INSERT INTO prompt_versions (id, template_id, version_no, instructions,"
                " temperature, change_note, content_hash)"
                " VALUES (:id, :template, 1, :instructions, CAST(:temperature AS numeric),"
                " :note, :hash)"
            ),
            {
                "id": version_id,
                "template": template_id,
                "instructions": instructions,
                "temperature": temperature,
                "note": "First platform default",
                "hash": _hash(instructions, temperature),
            },
        )
        bind.execute(
            sa.text("UPDATE prompt_templates SET active_version_id = :version WHERE id = :id"),
            {"version": version_id, "id": template_id},
        )
        bind.execute(
            sa.text(
                "INSERT INTO prompt_activations (id, template_id, version_id, action)"
                " VALUES (:id, :template, :version, 'ACTIVATE')"
            ),
            {
                "id": uuid.uuid5(_NAMESPACE, f"activation-{operation}-1"),
                "template": template_id,
                "version": version_id,
            },
        )


def downgrade() -> None:
    op.execute("""
        DROP TABLE prompt_activations, prompt_versions, prompt_templates;
        DROP FUNCTION prompt_history_refuse_change();
    """)
