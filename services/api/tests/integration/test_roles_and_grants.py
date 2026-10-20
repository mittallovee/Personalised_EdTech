"""M2 PR 2: migration 0004 (one Owner per coaching, grants, invited users) and /me grants."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError, IntegrityError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.identity.models import User
from qbank.modules.organizations.models import Membership, MembershipGrant
from tests.integration.conftest import (
    MEMBER_PASSWORD,
    PLATFORM,
    Coaching,
    MigratedDatabase,
    make_member,
)


@pytest.fixture
def client(migrated_database: MigratedDatabase) -> Iterator[TestClient]:
    settings = Settings(
        app_env=AppEnv.TEST, database_url=migrated_database.app_url, session_cookie_secure=False
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def sign_in(client: TestClient, email: str) -> int:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": MEMBER_PASSWORD})
    return response.status_code


def test_me_lists_faculty_grants_and_coaching_name(client: TestClient, owner_db: Database) -> None:
    faculty = make_member(
        owner_db, "FACULTY", grants=("QC", "PUBLISH"), coaching_name="Sharma Classes"
    )
    assert sign_in(client, faculty.email) == 200

    organization = client.get("/api/v1/me").json()["organization"]

    assert organization == {
        "id": str(faculty.org_id),
        "display_name": "Sharma Classes",
        "role": "FACULTY",
        "grants": ["PUBLISH", "QC"],
    }


def test_admin_holds_every_grant(client: TestClient, owner_db: Database) -> None:
    admin = make_member(owner_db, "ADMIN")
    assert sign_in(client, admin.email) == 200

    grants = client.get("/api/v1/me").json()["organization"]["grants"]

    assert grants == ["APPROVE", "EDIT_OTHERS", "MANAGE_AI_PROMPTS", "PUBLISH", "QC"]


def test_removed_grant_stops_on_the_next_request(client: TestClient, owner_db: Database) -> None:
    faculty = make_member(owner_db, "FACULTY", grants=("QC",))
    assert sign_in(client, faculty.email) == 200
    assert client.get("/api/v1/me").json()["organization"]["grants"] == ["QC"]

    with owner_db.transaction(TenantContext(organization_id=faculty.org_id)) as session:
        session.execute(
            MembershipGrant.__table__.delete().where(
                MembershipGrant.membership_id == faculty.membership_id
            )
        )

    assert client.get("/api/v1/me").json()["organization"]["grants"] == []


def test_invited_user_cannot_sign_in(client: TestClient, owner_db: Database) -> None:
    member = make_member(owner_db, "FACULTY")
    with owner_db.transaction(PLATFORM) as session:
        session.execute(update(User).where(User.id == member.user_id).values(status="INVITED"))

    assert sign_in(client, member.email) == 401


def test_a_coaching_has_at_most_one_active_owner(owner_db: Database) -> None:
    owner = make_member(owner_db, "OWNER")
    second = make_member(owner_db, "ADMIN", org_id=owner.org_id)

    with (
        pytest.raises(IntegrityError, match="memberships_one_owner_per_coaching"),
        owner_db.transaction(TenantContext(organization_id=owner.org_id)) as session,
    ):
        session.execute(
            update(Membership).where(Membership.id == second.membership_id).values(role="OWNER")
        )


def test_removed_owner_does_not_block_a_new_owner(owner_db: Database) -> None:
    owner = make_member(owner_db, "OWNER")
    second = make_member(owner_db, "ADMIN", org_id=owner.org_id)
    with owner_db.transaction(TenantContext(organization_id=owner.org_id)) as session:
        session.execute(
            update(Membership).where(Membership.id == owner.membership_id).values(status="REMOVED")
        )
        session.execute(
            update(Membership).where(Membership.id == second.membership_id).values(role="OWNER")
        )


# --- T18: isolation for membership_grants ---------------------------------------------------------


def grant(coaching: Coaching, name: str = "QC") -> MembershipGrant:
    return MembershipGrant(
        organization_id=coaching.org_id, membership_id=coaching.membership_id, grant_name=name
    )


def test_grants_of_another_coaching_are_invisible(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    with db.transaction(coaching_b.context) as session:
        session.add(grant(coaching_b))

    with db.transaction(coaching_a.context) as session:
        visible = set(session.scalars(select(MembershipGrant.membership_id)))
    assert coaching_b.membership_id not in visible

    with db.transaction(TenantContext()) as session:  # no coaching selected
        assert session.scalars(select(MembershipGrant)).all() == []


def test_grant_for_another_coaching_cannot_be_inserted(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    with (
        pytest.raises(DBAPIError, match="row-level security"),
        db.transaction(coaching_a.context) as session,
    ):
        session.add(grant(coaching_b))
        session.flush()


def test_grant_cannot_point_at_another_coachings_membership(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    """The composite key: even with a correct organization_id, the membership must belong to it."""
    with (
        pytest.raises(IntegrityError),
        db.transaction(coaching_a.context) as session,
    ):
        session.add(
            MembershipGrant(
                organization_id=coaching_a.org_id,
                membership_id=coaching_b.membership_id,
                grant_name="QC",
            )
        )
        session.flush()


def test_unknown_grant_name_is_rejected(db: Database, coaching_a: Coaching) -> None:
    with pytest.raises(IntegrityError), db.transaction(coaching_a.context) as session:
        session.add(grant(coaching_a, "SUPERUSER"))
        session.flush()
