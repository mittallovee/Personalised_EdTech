"""Who may do what (M2 design note §3). The only place these rules live; tested as a table (T13).

Every decision uses the ``Principal``, which is reloaded from the database on every request, so a
role or grant that was just removed stops working on the very next request (B-10). Nothing a
client sends (role, grant, coaching ID) is ever consulted.
"""

from enum import StrEnum
from uuid import UUID

from qbank.core.auth import Principal
from qbank.core.errors import PermissionDenied


class Role(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    FACULTY = "FACULTY"


class Grant(StrEnum):
    """Extra rights for faculty. Owner and admins hold all of them implicitly."""

    QC = "QC"
    APPROVE = "APPROVE"
    PUBLISH = "PUBLISH"
    EDIT_OTHERS = "EDIT_OTHERS"
    MANAGE_AI_PROMPTS = "MANAGE_AI_PROMPTS"


class Action(StrEnum):
    VIEW_MEMBERS = "VIEW_MEMBERS"
    # Invite/remove faculty, set faculty grants, make a faculty reset link.
    MANAGE_FACULTY = "MANAGE_FACULTY"
    # Invite an admin, promote/demote/remove admins, make an admin reset link.
    MANAGE_ADMINS = "MANAGE_ADMINS"
    TRANSFER_OWNERSHIP = "TRANSFER_OWNERSHIP"
    VIEW_AUDIT_LOG = "VIEW_AUDIT_LOG"
    # Platform only: create/rename/suspend coachings, make an Owner's reset link.
    MANAGE_COACHINGS = "MANAGE_COACHINGS"
    # Read the syllabus, exams, sources and other lists a question refers to (M3).
    VIEW_CATALOGUES = "VIEW_CATALOGUES"
    # Add, rename and retire syllabus items, exams and sources; import them (M3).
    MANAGE_CATALOGUES = "MANAGE_CATALOGUES"
    # Start a question or passage (M3). Opening someone else's draft: see ``may_access_draft``.
    CREATE_QUESTIONS = "CREATE_QUESTIONS"


_ADMINS = frozenset({Role.OWNER, Role.ADMIN})
_EVERYONE = frozenset(Role)

# Which coaching roles may do each action inside their own coaching.
_ROLES_ALLOWED: dict[Action, frozenset[Role]] = {
    Action.VIEW_MEMBERS: _ADMINS,
    Action.MANAGE_FACULTY: _ADMINS,
    Action.MANAGE_ADMINS: frozenset({Role.OWNER}),
    Action.TRANSFER_OWNERSHIP: frozenset({Role.OWNER}),
    Action.VIEW_AUDIT_LOG: _ADMINS,
    Action.MANAGE_COACHINGS: frozenset(),
    Action.VIEW_CATALOGUES: _EVERYONE,
    Action.MANAGE_CATALOGUES: _ADMINS,
    Action.CREATE_QUESTIONS: _EVERYONE,
}

# Platform admins may do these without acting in a coaching (they work on platform-level data).
_PLATFORM_LEVEL = frozenset({Action.MANAGE_COACHINGS, Action.VIEW_AUDIT_LOG})


def is_allowed(principal: Principal, action: Action) -> bool:
    # Platform admins have full authority inside the coaching they explicitly act in (A-06).
    acting = principal.acting_organization_id is not None
    if principal.is_platform_admin and (acting or action in _PLATFORM_LEVEL):
        return True
    return principal.role is not None and Role(principal.role) in _ROLES_ALLOWED[action]


def require(principal: Principal, action: Action) -> None:
    if not is_allowed(principal, action):
        raise PermissionDenied("You don't have permission to do this.")


def may_manage_member(principal: Principal, member_role: str) -> bool:
    """May invite a member with this role, or make them a new activation or reset link?

    Faculty: Owner and admins. Admins: the Owner. The Owner: only a platform admin acting in the
    coaching (nobody inside it can take over the Owner's account).
    """
    if Role(member_role) is Role.OWNER:
        return principal.is_platform_admin and principal.acting_organization_id is not None
    action = Action.MANAGE_ADMINS if Role(member_role) is Role.ADMIN else Action.MANAGE_FACULTY
    return is_allowed(principal, action)


def require_may_manage_member(principal: Principal, member_role: str) -> None:
    if not may_manage_member(principal, member_role):
        raise PermissionDenied("You don't have permission to do this.")


def has_grant(principal: Principal, grant: Grant) -> bool:
    if principal.is_platform_admin and principal.acting_organization_id is not None:
        return True
    if principal.role is not None and Role(principal.role) in _ADMINS:
        return True
    return grant in principal.grants


def may_access_draft(principal: Principal, author_id: UUID) -> bool:
    """Read or edit a draft: its author, admins, and faculty with ``EDIT_OTHERS`` (M3 §6).

    Someone with no role in the coaching (removed, suspended) may open nothing, not even their own.
    """
    if not is_allowed(principal, Action.CREATE_QUESTIONS):
        return False
    return principal.user_id == author_id or has_grant(principal, Grant.EDIT_OTHERS)
