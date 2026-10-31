"""M2 exit test T13 (rules part): the full "who may do what" table from the M2 design note §3."""

from uuid import UUID

import pytest

from qbank.core.auth import Principal
from qbank.core.errors import PermissionDenied
from qbank.core.ids import new_id
from qbank.core.permissions import (
    Action,
    Grant,
    has_grant,
    is_allowed,
    may_access_draft,
    may_manage_member,
    require,
    require_may_manage_member,
)

COACHING = new_id()


def principal(
    role: str | None,
    *,
    platform: bool = False,
    acting: UUID | None = None,
    grants: frozenset[str] = frozenset(),
) -> Principal:
    return Principal(
        user_id=new_id(),
        display_name="Someone",
        is_platform_admin=platform,
        organization_id=COACHING if role else None,
        role=role,
        acting_organization_id=acting,
        grants=grants,
    )


FACULTY = principal("FACULTY", grants=frozenset({"QC", "APPROVE", "PUBLISH"}))
ADMIN = principal("ADMIN")
OWNER = principal("OWNER")
PLATFORM = principal(None, platform=True)
PLATFORM_ACTING = principal(None, platform=True, acting=COACHING)

# Columns: Faculty (even with every grant), Admin, Owner, Platform (not acting), Platform (acting).
TABLE = {
    Action.VIEW_MEMBERS: (False, True, True, False, True),
    Action.MANAGE_FACULTY: (False, True, True, False, True),
    Action.MANAGE_ADMINS: (False, False, True, False, True),
    Action.TRANSFER_OWNERSHIP: (False, False, True, False, True),
    Action.VIEW_AUDIT_LOG: (False, True, True, True, True),
    Action.MANAGE_COACHINGS: (False, False, False, True, True),
    Action.VIEW_CATALOGUES: (True, True, True, False, True),
    Action.MANAGE_CATALOGUES: (False, True, True, False, True),
    Action.CREATE_QUESTIONS: (True, True, True, False, True),
}
WHO = (FACULTY, ADMIN, OWNER, PLATFORM, PLATFORM_ACTING)


def test_table_covers_every_action() -> None:
    assert set(TABLE) == set(Action)


@pytest.mark.parametrize("action", list(Action))
def test_each_role_gets_exactly_the_actions_in_the_table(action: Action) -> None:
    assert tuple(is_allowed(who, action) for who in WHO) == TABLE[action]


def test_someone_without_a_coaching_role_may_do_nothing() -> None:
    nobody = principal(None)
    assert not any(is_allowed(nobody, action) for action in Action)


def test_require_raises_permission_denied() -> None:
    require(OWNER, Action.MANAGE_ADMINS)  # allowed: no error
    with pytest.raises(PermissionDenied) as raised:
        require(ADMIN, Action.MANAGE_ADMINS)
    assert raised.value.code == "PERMISSION_DENIED"


def test_faculty_has_only_the_grants_they_were_given() -> None:
    faculty = principal("FACULTY", grants=frozenset({"QC"}))
    assert has_grant(faculty, Grant.QC)
    assert not has_grant(faculty, Grant.PUBLISH)


@pytest.mark.parametrize("who", [ADMIN, OWNER, PLATFORM_ACTING])
def test_admins_owner_and_acting_platform_hold_every_grant(who: Principal) -> None:
    assert all(has_grant(who, grant) for grant in Grant)


def test_platform_admin_not_acting_in_a_coaching_holds_no_grant() -> None:
    assert not any(has_grant(PLATFORM, grant) for grant in Grant)


# Who may invite a member of each role, or make them a new link (design note §3).
# Columns as above: Faculty, Admin, Owner, Platform (not acting), Platform (acting).
MANAGE_MEMBER = {
    "FACULTY": (False, True, True, False, True),
    "ADMIN": (False, False, True, False, True),
    "OWNER": (False, False, False, False, True),
}


@pytest.mark.parametrize("member_role", list(MANAGE_MEMBER))
def test_who_may_manage_a_member_of_each_role(member_role: str) -> None:
    allowed = tuple(may_manage_member(who, member_role) for who in WHO)
    assert allowed == MANAGE_MEMBER[member_role]


def test_require_may_manage_member_raises_permission_denied() -> None:
    require_may_manage_member(OWNER, "ADMIN")  # allowed: no error
    with pytest.raises(PermissionDenied):
        require_may_manage_member(OWNER, "OWNER")


# Who may read or edit a draft that someone else wrote (M3 design note section 6).
def test_a_draft_is_open_to_its_author_admins_and_those_granted_edit_others() -> None:
    author = FACULTY
    other = principal("FACULTY")
    other_with_grant = principal("FACULTY", grants=frozenset({"EDIT_OTHERS"}))
    assert may_access_draft(author, author.user_id)
    assert not may_access_draft(other, author.user_id)
    assert may_access_draft(other_with_grant, author.user_id)
    for admin in (ADMIN, OWNER, PLATFORM_ACTING):
        assert may_access_draft(admin, author.user_id)


def test_nobody_without_a_role_may_open_a_draft_even_their_own() -> None:
    nobody = principal(None)
    assert not may_access_draft(nobody, nobody.user_id)
    assert not may_access_draft(PLATFORM, PLATFORM.user_id)
