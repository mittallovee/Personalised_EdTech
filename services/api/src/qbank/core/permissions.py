"""Who may do what (M2 design note §3). The only place these rules live; tested as a table (T13).

Every decision uses the ``Principal``, which is reloaded from the database on every request, so a
role or grant that was just removed stops working on the very next request (B-10). Nothing a
client sends (role, grant, coaching ID) is ever consulted.
"""

from enum import StrEnum

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


_ADMINS = frozenset({Role.OWNER, Role.ADMIN})

# Which coaching roles may do each action inside their own coaching.
_ROLES_ALLOWED: dict[Action, frozenset[Role]] = {
    Action.VIEW_MEMBERS: _ADMINS,
    Action.MANAGE_FACULTY: _ADMINS,
    Action.MANAGE_ADMINS: frozenset({Role.OWNER}),
    Action.TRANSFER_OWNERSHIP: frozenset({Role.OWNER}),
    Action.VIEW_AUDIT_LOG: _ADMINS,
    Action.MANAGE_COACHINGS: frozenset(),
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


def has_grant(principal: Principal, grant: Grant) -> bool:
    if principal.is_platform_admin and principal.acting_organization_id is not None:
        return True
    if principal.role is not None and Role(principal.role) in _ADMINS:
        return True
    return grant in principal.grants
