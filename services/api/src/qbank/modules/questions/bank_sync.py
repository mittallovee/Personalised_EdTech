"""Keeping the bank index in step with the questions (M4 design note §7.1).

``sync_bank`` works out one question's row from its own tables and hands it to the search module;
every change to a question calls it inside the same transaction, so the index is never stale.
``reindex_bank`` does the same for every question of a coaching, which is what ``qbank
reindex-bank`` runs after a bug fix or a change to what is indexed. Both go through ``bank_entry``,
so the incremental write and the rebuild cannot disagree, and a test checks that they do not.

The row shows the *bank version*: the published version if there is one, else the newest.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from qbank.modules.questions.bank_fields import bank_fields
from qbank.modules.questions.bank_text import bank_text
from qbank.modules.questions.domain.workflow import PRIVATE_STATES
from qbank.modules.questions.duplicate_key import duplicate_key
from qbank.modules.questions.models import QuestionMaster, QuestionRevision, QuestionVersion
from qbank.modules.search.public import BankEntry, save_entry

_PRIVATE = frozenset(state.value for state in PRIVATE_STATES)
BATCH = 500


def _shown_revision(session: Session, version: QuestionVersion) -> QuestionRevision:
    """The text the bank reads: the frozen revision under review or published, else the working
    copy (a draft, a returned question)."""
    if version.review_revision_id is not None:
        reviewed = session.get(QuestionRevision, version.review_revision_id)
        if reviewed is not None:
            return reviewed
    return session.scalars(
        select(QuestionRevision).where(
            QuestionRevision.version_id == version.id, QuestionRevision.frozen_at.is_(None)
        )
    ).one()


def bank_entry(session: Session, master: QuestionMaster) -> BankEntry:
    """The index row of one question, worked out from its tables alone."""
    versions = list(
        session.scalars(
            select(QuestionVersion)
            .where(QuestionVersion.master_id == master.id)
            .order_by(QuestionVersion.number)
        )
    )
    newest = versions[-1]
    published = next((v for v in versions if v.id == master.published_version_id), None)
    shown = published or newest
    revision = _shown_revision(session, shown)
    fields = bank_fields(revision.content)
    text = bank_text(revision.content)
    # Worked out from the rows, not from the clock, so a rebuild gives the same answer.
    moments: list[datetime] = [
        master.created_at,
        shown.state_changed_at,
        revision.updated_at,
        newest.created_at,
    ]
    if master.archived_at is not None:
        moments.append(master.archived_at)
    return BankEntry(
        organization_id=master.organization_id,
        master_id=master.id,
        code=master.code,
        created_by=master.created_by,
        created_at=master.created_at,
        updated_at=max(moments),
        version_number=shown.number,
        state=shown.state,
        is_private=shown.state in _PRIVATE,
        is_archived=master.archived_at is not None,
        has_published=published is not None,
        has_open_correction=published is not None and newest.id != published.id,
        question_type=fields.question_type,
        language=fields.language,
        class_id=fields.class_id,
        subject_id=fields.subject_id,
        chapter_id=fields.chapter_id,
        topic_id=fields.topic_id,
        primary_concept_id=fields.primary_concept_id,
        concept_ids=fields.concept_ids,
        difficulty=fields.difficulty,
        bloom_level=fields.bloom_level,
        is_pyq=fields.is_pyq,
        exam_id=fields.exam_id,
        exam_year=fields.exam_year,
        has_solution=fields.has_solution,
        has_video=fields.has_video,
        stem_text=text.stem_text,
        preview=text.preview,
        duplicate_key=duplicate_key(revision.content),
        match_text=text.match_text,
    )


def sync_bank(session: Session, master: QuestionMaster) -> None:
    """Bring the question's row up to date, in the caller's transaction."""
    session.flush()  # the row is read back from the tables, so what was changed must be there
    save_entry(session, bank_entry(session, master))


def reindex_bank(
    session: Session, organization_id: UUID, *, after: UUID | None = None
) -> tuple[int, UUID | None]:
    """Rebuild the rows of up to ``BATCH`` of this coaching's questions, in id order after
    ``after``. Returns how many were rebuilt, and the id to continue after (``None`` when the
    coaching is done)."""
    query = (
        select(QuestionMaster)
        .where(QuestionMaster.organization_id == organization_id)
        .order_by(QuestionMaster.id)
        .limit(BATCH)
        # Every writer locks the question first, so a rebuild waits for a change in progress and
        # reads what it committed; otherwise it could write back a row worked out before it.
        # The locks last until the batch commits, which is a few seconds at most.
        .with_for_update()
    )
    if after is not None:
        query = query.where(QuestionMaster.id > after)
    masters = list(session.scalars(query))
    for master in masters:
        save_entry(session, bank_entry(session, master))
    return len(masters), (masters[-1].id if len(masters) == BATCH else None)
