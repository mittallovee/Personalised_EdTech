"""Fill a load-test database with a coaching and 100,000 synthetic questions (K-08).

    MIGRATION_DATABASE_URL=postgresql+psycopg://owner:...@host:5432/qbank_load \\
    LOAD_TEST_PASSWORD=... uv run python -m tests.load.seed_bank --questions 100000 \\
        --users-out load-users.json

Refuses unless the database name ends in ``_load``: it is never pointed at real data. It creates
one coaching with an owner, an admin and six faculty (one with edit-others, one with QC) whose
password is ``LOAD_TEST_PASSWORD``, writes their emails to ``--users-out`` for the k6 scripts, and
inserts the questions in batches of 1,000 (one transaction each) with plain SQL, walking each one
through the real workflow states so the database triggers check every row. Then it rebuilds the
bank index with the same ``reindex_bank`` the ``qbank reindex-bank`` command runs, and times it.

Made-up text only (``synthetic.py``); the generated data is never committed.
"""

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from qbank.core.codes import generate_code
from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.security import hash_password
from qbank.core.tenancy import TenantContext
from qbank.modules.identity.models import PasswordCredential, User
from qbank.modules.organizations.models import Membership, MembershipGrant, Organization
from qbank.modules.questions.public import reindex_bank
from qbank.modules.questions.service import content_hash
from tests.load.synthetic import Syllabus, make_syllabus, synthetic_question

BATCH = 1_000
SHORTEST_SECRET = 12  # characters
PLATFORM = TenantContext(is_platform=True)

# Share of each state in the synthetic bank (the rest are drafts), and of archived questions.
STATES = (
    ("PUBLISHED", 0.70),
    ("APPROVED", 0.03),
    ("QC_PASSED", 0.03),
    ("IN_REVIEW", 0.08),
    ("CHANGES_REQUESTED", 0.03),
)
ARCHIVED = 0.02
MEMBERS = (
    ("owner", "OWNER", ()),
    ("admin", "ADMIN", ()),
    ("editor", "FACULTY", ("EDIT_OTHERS",)),
    ("qc", "FACULTY", ("QC",)),
    ("faculty1", "FACULTY", ()),
    ("faculty2", "FACULTY", ()),
    ("faculty3", "FACULTY", ()),
    ("faculty4", "FACULTY", ()),
)


@dataclass(frozen=True, slots=True)
class LoadMember:
    name: str
    email: str
    role: str
    user_id: UUID


def _state(rng: random.Random) -> str:
    draw, total = rng.random(), 0.0
    for state, share in STATES:
        total += share
        if draw < total:
            return state
    return "DRAFT"


def create_coaching(
    database: Database, password_hash: str, seed: int
) -> tuple[UUID, list[LoadMember]]:
    org_id = new_id()
    members: list[LoadMember] = []
    with database.transaction(PLATFORM) as session:
        session.add(Organization(id=org_id, display_name=f"Load test coaching {seed}"))
        for name, role, _ in MEMBERS:
            user_id = new_id()
            email = f"load-{seed}-{name}@example.com"
            session.add(User(id=user_id, display_name=f"Load {name}"))
            session.flush()
            session.add(
                PasswordCredential(user_id=user_id, email=email, password_hash=password_hash)
            )
            session.execute(
                text("INSERT INTO account_emails (email, user_id) VALUES (:email, :user_id)"),
                {"email": email, "user_id": user_id},
            )
            members.append(LoadMember(name, email, role, user_id))
    with database.transaction(TenantContext(organization_id=org_id)) as session:
        for member, (_, role, grants) in zip(members, MEMBERS, strict=True):
            membership_id = new_id()
            session.add(
                Membership(
                    id=membership_id, organization_id=org_id, user_id=member.user_id, role=role
                )
            )
            session.flush()
            for grant in grants:
                session.add(
                    MembershipGrant(
                        organization_id=org_id, membership_id=membership_id, grant_name=grant
                    )
                )
    return org_id, members


def _insert_batch(
    session: Session,
    org: UUID,
    authors: list[UUID],
    publisher: UUID,
    syllabus: Syllabus,
    rng: random.Random,
    moments: list[datetime],
    codes: set[str],
) -> None:
    now = datetime.now(UTC)
    masters, versions, revisions, frozen, working = [], [], [], [], []
    to_state: dict[str, list[UUID]] = {state: [] for state, _ in STATES}
    published, archived = [], []
    for created in moments:
        code = generate_code()
        while code in codes:
            code = generate_code()
        codes.add(code)
        master_id, version_id, revision_id = new_id(), new_id(), new_id()
        author = rng.choice(authors)
        content = synthetic_question(rng, syllabus)
        body = json.dumps(content, ensure_ascii=False)
        state = _state(rng)
        moved = min(created + timedelta(days=rng.uniform(0.5, 20)), now)
        masters.append({"id": master_id, "org": org, "code": code, "by": author, "at": created})
        versions.append({"id": version_id, "org": org, "master": master_id, "at": created})
        revisions.append(
            {
                "id": revision_id,
                "org": org,
                "version": version_id,
                "number": 1,
                "revision": 1,
                "content": body,
                "by": author,
                "at": created,
                "updated": created,
            }
        )
        if state != "DRAFT":
            frozen.append({"id": revision_id, "hash": content_hash(content), "at": moved})
            working.append(
                {
                    "id": new_id(),
                    "org": org,
                    "version": version_id,
                    "number": 2,
                    "revision": 2,
                    "content": body,
                    "by": author,
                    "at": moved,
                    "updated": moved,
                }
            )
            to_state[state].append(version_id)
        if state == "PUBLISHED":
            published.append(
                {
                    "id": new_id(),
                    "org": org,
                    "version": version_id,
                    "revision": revision_id,
                    "by": publisher,
                    "at": moved,
                    "hash": content_hash(content),
                    "master": master_id,
                }
            )
        if rng.random() < ARCHIVED:
            archived.append({"id": master_id, "at": min(moved + timedelta(days=1), now)})

    session.execute(
        text(
            "INSERT INTO public_codes (code, entity_type, organization_id)"
            " VALUES (:code, 'question', :org)"
        ),
        [{"code": m["code"], "org": org} for m in masters],
    )
    session.execute(
        text(
            "INSERT INTO question_masters (id, organization_id, code, created_by, created_at)"
            " VALUES (:id, :org, :code, :by, :at)"
        ),
        masters,
    )
    session.execute(
        text(
            "INSERT INTO question_versions"
            " (id, organization_id, master_id, number, created_at, state_changed_at)"
            " VALUES (:id, :org, :master, 1, :at, :at)"
        ),
        versions,
    )
    insert_revision = text(
        "INSERT INTO question_revisions (id, organization_id, version_id, number, revision,"
        " content, author_id, created_at, updated_at)"
        " VALUES (:id, :org, :version, :number, :revision, CAST(:content AS jsonb), :by, :at,"
        " :updated)"
    )
    session.execute(insert_revision, revisions)
    if frozen:
        # As a submit does: freeze the working copy, then start a new working copy of it.
        session.execute(
            text(
                "UPDATE question_revisions SET frozen_at = :at, content_hash = :hash WHERE id = :id"
            ),
            frozen,
        )
        session.execute(insert_revision, working)
        session.execute(
            text(
                "UPDATE question_versions v SET state = 'IN_REVIEW', flow_revision = 2,"
                " review_revision_id = r.id, state_changed_at = r.frozen_at"
                " FROM question_revisions r"
                " WHERE r.version_id = v.id AND r.number = 1 AND v.id = ANY(:ids)"
            ),
            {"ids": [v for ids in to_state.values() for v in ids]},
        )
    # Each later step one at a time, as the triggers allow, over the whole batch at once.
    steps = (
        ("CHANGES_REQUESTED", 3, ("CHANGES_REQUESTED",)),
        ("QC_PASSED", 3, ("QC_PASSED", "APPROVED", "PUBLISHED")),
        ("APPROVED", 4, ("APPROVED", "PUBLISHED")),
        ("PUBLISHED", 5, ("PUBLISHED",)),
    )
    for state, flow, targets in steps:
        ids = [v for target in targets for v in to_state[target]]
        if not ids:
            continue
        session.execute(
            text(
                "UPDATE question_versions SET state = :state, flow_revision = :flow,"
                " review_revision_id = CASE WHEN :returned THEN NULL ELSE review_revision_id END"
                " WHERE id = ANY(:ids)"
            ),
            {"state": state, "flow": flow, "returned": state == "CHANGES_REQUESTED", "ids": ids},
        )
    if published:
        session.execute(
            text(
                "INSERT INTO published_versions (id, organization_id, version_id, revision_id,"
                " published_by, published_at, content_hash, labels)"
                " VALUES (:id, :org, :version, :revision, :by, :at, :hash, '{}'::jsonb)"
            ),
            published,
        )
        session.execute(
            text("UPDATE question_masters SET published_version_id = :version WHERE id = :master"),
            published,
        )
    if archived:
        session.execute(
            text("UPDATE question_masters SET archived_at = :at WHERE id = :id"), archived
        )


def seed(database: Database, *, questions: int, seed: int, password_hash: str) -> dict[str, Any]:
    """Seed the bank. The members' password arrives already hashed, so nothing here can print it."""
    rng = random.Random(seed)  # noqa: S311 - made-up data that must repeat, not a secret
    org, members = create_coaching(database, password_hash, seed)
    authors = [m.user_id for m in members]
    publisher = members[0].user_id
    syllabus = make_syllabus(rng)
    start = datetime.now(UTC) - timedelta(days=730)
    step = timedelta(days=700) / max(questions, 1)
    codes: set[str] = set()
    began = time.monotonic()
    for first in range(0, questions, BATCH):
        moments = [start + step * i for i in range(first, min(first + BATCH, questions))]
        with database.transaction(TenantContext(organization_id=org)) as session:
            _insert_batch(session, org, authors, publisher, syllabus, rng, moments, codes)
        print(f"  {min(first + BATCH, questions)} questions", file=sys.stderr, flush=True)
    inserted = time.monotonic() - began

    began = time.monotonic()
    indexed, after = 0, None
    while True:
        with database.transaction(TenantContext(organization_id=org)) as session:
            done, after = reindex_bank(session, org, after=after)
        indexed += done
        if after is None:
            break
    reindexed = time.monotonic() - began
    with database.transaction(TenantContext(organization_id=org)) as session:
        session.execute(text("ANALYZE"))
    return {
        "organization_id": str(org),
        "questions": questions,
        "indexed": indexed,
        "insert_seconds": round(inserted, 1),
        "reindex_seconds": round(reindexed, 1),
        "users": [{"name": m.name, "email": m.email, "role": m.role} for m in members],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seed_bank", description=__doc__.splitlines()[0])
    parser.add_argument("--questions", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--users-out", type=Path, required=True)
    args = parser.parse_args(argv)
    url = os.environ.get("MIGRATION_DATABASE_URL", "")
    password = os.environ.get("LOAD_TEST_PASSWORD", "")
    if not url:
        print("Set MIGRATION_DATABASE_URL (table-owner connection).", file=sys.stderr)
        return 2
    name = make_url(url).database or ""
    if not name.endswith("_load"):
        print(f"Refusing: the database '{name}' does not end in _load.", file=sys.stderr)
        return 2
    if len(password) < SHORTEST_SECRET:
        print("Set LOAD_TEST_PASSWORD (at least 12 characters).", file=sys.stderr)
        return 2
    password_hash = hash_password(password)
    del password
    if args.questions < 1:
        print("--questions must be at least 1.", file=sys.stderr)
        return 2
    database = Database(url)
    try:
        summary = seed(
            database, questions=args.questions, seed=args.seed, password_hash=password_hash
        )
    finally:
        database.dispose()
    args.users_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "users"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
