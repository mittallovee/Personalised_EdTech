"""M1 exit tests T1, T2 and T4: one coaching can never see or change another's rows (ADR-0005)."""

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError

from qbank.core.db import Database
from qbank.core.ids import new_id
from qbank.core.tenancy import NO_CONTEXT, TenantContext
from qbank.modules.audit.models import AuditEvent
from qbank.modules.identity.models import User
from qbank.modules.organizations.models import Membership, Organization
from tests.integration.conftest import Coaching

RLS_VIOLATION = "row-level security"


def test_coaching_sees_only_its_own_rows(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    with db.transaction(coaching_a.context) as session:
        org_ids = set(session.scalars(select(Organization.id)))
        membership_ids = set(session.scalars(select(Membership.id)))
        user_ids = set(session.scalars(select(User.id)))
        audit_ids = set(session.scalars(select(AuditEvent.id)))

    assert org_ids == {coaching_a.org_id}
    assert coaching_a.membership_id in membership_ids
    assert coaching_b.membership_id not in membership_ids
    assert coaching_a.user_id in user_ids
    assert coaching_b.user_id not in user_ids
    assert coaching_a.audit_id in audit_ids
    assert coaching_b.audit_id not in audit_ids


def test_guessed_id_of_other_coaching_is_invisible(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    with db.transaction(coaching_a.context) as session:
        found = session.get(Membership, coaching_b.membership_id)

    assert found is None


def test_update_of_other_coaching_affects_no_rows(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    with db.transaction(coaching_a.context) as session:
        result = session.execute(
            update(Membership).where(Membership.id == coaching_b.membership_id).values(role="ADMIN")
        )

    assert result.rowcount == 0  # type: ignore[attr-defined]
    with db.transaction(coaching_b.context) as session:
        assert session.get(Membership, coaching_b.membership_id).role == "OWNER"  # type: ignore[union-attr]


def test_insert_into_other_coaching_is_rejected(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    """T4: a row whose organization differs from the context fails the policy's WITH CHECK."""
    with (
        pytest.raises(DBAPIError, match=RLS_VIOLATION),
        db.transaction(coaching_a.context) as session,
    ):
        session.add(
            Membership(
                id=new_id(),
                organization_id=coaching_b.org_id,
                user_id=coaching_a.user_id,
                role="FACULTY",
            )
        )
        session.flush()


def test_moving_a_row_to_other_coaching_is_rejected(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    with (
        pytest.raises(DBAPIError, match=RLS_VIOLATION),
        db.transaction(coaching_a.context) as session,
    ):
        session.execute(
            update(Membership)
            .where(Membership.id == coaching_a.membership_id)
            .values(organization_id=coaching_b.org_id)
        )


def test_tenant_cannot_create_coachings(db: Database, coaching_a: Coaching) -> None:
    with (
        pytest.raises(DBAPIError, match=RLS_VIOLATION),
        db.transaction(coaching_a.context) as session,
    ):
        session.add(Organization(id=new_id(), display_name="Sneaky"))
        session.flush()


def test_missing_context_returns_nothing(db: Database, coaching_a: Coaching) -> None:
    """T2: forgetting to set a context fails closed."""
    with db.transaction(NO_CONTEXT) as session:
        assert session.scalars(select(Organization)).all() == []
        assert session.scalars(select(Membership)).all() == []
        assert session.scalars(select(User)).all() == []
        assert session.scalars(select(AuditEvent)).all() == []


def test_context_does_not_leak_to_next_transaction(db: Database, coaching_a: Coaching) -> None:
    """Pooled connections are reused; the context is transaction-local and must not carry over."""
    with db.transaction(coaching_a.context) as session:
        assert session.scalar(text("SELECT app_current_org()")) == coaching_a.org_id

    with db.transaction(NO_CONTEXT) as session:
        assert session.scalar(text("SELECT app_current_org()")) is None
        assert session.scalars(select(Membership)).all() == []


def test_platform_admin_acting_in_a_coaching_sees_that_coaching(
    db: Database, coaching_a: Coaching, coaching_b: Coaching
) -> None:
    acting_in_b = TenantContext(organization_id=coaching_b.org_id, is_platform=True)
    with db.transaction(acting_in_b) as session:
        membership_ids = set(session.scalars(select(Membership.id)))

    assert coaching_b.membership_id in membership_ids
    assert coaching_a.membership_id not in membership_ids
