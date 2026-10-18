"""M1 exit test T11: codes are unique across all coachings, retried on collision, never changed."""

from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from qbank.core import codes
from qbank.core.codes import ALPHABET, reserve_code
from qbank.core.db import Database
from tests.integration.conftest import Coaching


def fixed_codes(monkeypatch: pytest.MonkeyPatch, sequence: list[str]) -> None:
    values: Iterator[str] = iter(sequence)
    monkeypatch.setattr(codes, "generate_code", lambda: next(values))


def test_reserved_code_is_stored_for_the_coaching(db: Database, coaching_a: Coaching) -> None:
    with db.transaction(coaching_a.context) as session:
        code = reserve_code(session, entity_type="question", organization_id=coaching_a.org_id)
        stored = session.execute(
            text("SELECT entity_type FROM public_codes WHERE code = :c"), {"c": code}
        ).scalar()

    assert len(code) == 8 and set(code) <= set(ALPHABET)
    assert stored == "question"


def test_collision_with_another_coachings_code_is_retried(
    db: Database, coaching_a: Coaching, coaching_b: Coaching, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed_codes(monkeypatch, ["AAAA0001"])
    with db.transaction(coaching_b.context) as session:
        reserve_code(session, entity_type="question", organization_id=coaching_b.org_id)

    fixed_codes(monkeypatch, ["AAAA0001", "AAAA0002"])  # first try collides with B's code
    with db.transaction(coaching_a.context) as session:
        visible = session.execute(
            text("SELECT count(*) FROM public_codes WHERE code = 'AAAA0001'")
        ).scalar()
        code = reserve_code(session, entity_type="question", organization_id=coaching_a.org_id)

    assert visible == 0  # A cannot see B's code ...
    assert code == "AAAA0002"  # ... but uniqueness still holds across coachings


def test_gives_up_after_repeated_collisions(
    db: Database, coaching_a: Coaching, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixed_codes(monkeypatch, ["BBBB0001"])
    with db.transaction(coaching_a.context) as session:
        reserve_code(session, entity_type="question", organization_id=coaching_a.org_id)

    fixed_codes(monkeypatch, ["BBBB0001"] * codes.MAX_ATTEMPTS)
    with (
        pytest.raises(RuntimeError, match="unique code"),
        db.transaction(coaching_a.context) as session,
    ):
        reserve_code(session, entity_type="question", organization_id=coaching_a.org_id)


def test_codes_cannot_be_changed_or_deleted(db: Database, coaching_a: Coaching) -> None:
    with db.transaction(coaching_a.context) as session:
        code = reserve_code(session, entity_type="question", organization_id=coaching_a.org_id)

    for statement in (
        "UPDATE public_codes SET entity_type = 'x' WHERE code = :c",
        "DELETE FROM public_codes WHERE code = :c",
    ):
        with (
            pytest.raises(DBAPIError, match="permission denied"),
            db.transaction(coaching_a.context) as session,
        ):
            session.execute(text(statement), {"c": code})
