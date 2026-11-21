"""The prompt library (M5 design note §10; prompt spec PL-01 to PL-11).

What the AI is told is editable, versioned and traceable. Three levels: the **platform's** default
(ours), the **coaching's** own prompt for an operation (optionally for one translation language),
and a person's **personal** prompts. A saved version is never changed: an edit is a new version,
and which version is in use is a separate, recorded switch (activate, roll back, reset). Only the
instructions are editable; the safety preamble, the placeholders and the output format are locked
in code (``locked.py``).

Who may do what: everyone may read the platform and coaching prompts and keep personal ones; a
faculty member with the ``MANAGE_AI_PROMPTS`` grant (and an admin) writes and activates the
coaching's; only a platform admin writes the platform's; a personal prompt is visible to its
author and to admins.
"""

import difflib
import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from qbank.core.auth import Principal
from qbank.core.errors import (
    Conflict,
    NotFound,
    PermissionDenied,
    PreconditionFailed,
    ValidationFailed,
)
from qbank.core.etag import require_if_match
from qbank.core.permissions import Action, Grant, has_grant, is_allowed, require
from qbank.modules.ai import locked
from qbank.modules.ai.models import PromptActivation, PromptTemplate, PromptVersion
from qbank.modules.ai.names import Operation, Scope
from qbank.modules.audit.public import record_event
from qbank.modules.notifications.public import notify
from qbank.modules.organizations.public import admin_user_ids
from qbank.modules.taxonomy.public import language_names

ENTITY_TYPE = "prompt_template"
_SECRETS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]{16,}"),
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9+/_-]{40,}={0,2}(?![A-Za-z0-9])"),
)


@dataclass(frozen=True, slots=True)
class Problem:
    code: str
    message: str


def content_hash(instructions: str, temperature: Decimal | None) -> str:
    """A fingerprint of a prompt's text and setting (the same rule the seeded defaults used)."""
    shown = "" if temperature is None else format(temperature, "f")
    return hashlib.sha256(f"{instructions}\n{shown}".encode()).hexdigest()


def check_instructions(operation: Operation, instructions: str) -> list[Problem]:
    """Everything wrong with the text, so an editor can show it all at once (PL-05)."""
    problems: list[Problem] = []
    if not instructions.strip():
        return [Problem("EMPTY", "Write the instructions.")]
    if len(instructions) > locked.MOST_INSTRUCTION_CHARS:
        problems.append(
            Problem(
                "TOO_LONG",
                f"At most {locked.MOST_INSTRUCTION_CHARS} characters (it has {len(instructions)}).",
            )
        )
    if "\x00" in instructions:
        problems.append(Problem("CONTROL_CHARACTERS", "The text contains a control character."))
    rules = locked.PLACEHOLDERS[operation]
    used = locked.slots_in(instructions)
    for name in dict.fromkeys(used):
        if name not in rules.allowed:
            allowed = ", ".join("{{" + n + "}}" for n in sorted(rules.allowed))
            problems.append(
                Problem(
                    "UNKNOWN_PLACEHOLDER",
                    "{{"
                    + name
                    + "}} is not available for this operation. Use only: "
                    + allowed
                    + " (lower-case).",
                )
            )
    for name in sorted(rules.required - set(used)):
        problems.append(
            Problem("MISSING_PLACEHOLDER", "{{" + name + "}} must appear in the instructions.")
        )
    if locked.has_stray_braces(instructions):
        problems.append(
            Problem("MALFORMED_PLACEHOLDER", "A {{ or }} is not part of a complete {{name}}.")
        )
    if any(pattern.search(instructions) for pattern in _SECRETS):
        problems.append(
            Problem(
                "LOOKS_LIKE_A_SECRET",
                "The text contains something that looks like a key or token. Never put those"
                " in a prompt.",
            )
        )
    return problems


def require_valid(operation: Operation, instructions: str) -> None:
    problems = check_instructions(operation, instructions)
    if problems:
        raise ValidationFailed(
            "This prompt cannot be used.",
            code="AI_PROMPT_INVALID",
            details={"problems": [{"code": p.code, "message": p.message} for p in problems]},
        )


# --- Reading ------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TemplateView:
    template: PromptTemplate
    active: PromptVersion | None  # the version in use; for a personal prompt, the latest one
    latest: PromptVersion | None
    update_available: PromptVersion | None  # a newer platform default this coaching has not seen


def _platform_template(session: Session, operation: str) -> PromptTemplate | None:
    return session.scalars(
        select(PromptTemplate).where(
            PromptTemplate.scope == Scope.PLATFORM.value, PromptTemplate.operation == operation
        )
    ).first()


def _version(session: Session, version_id: UUID | None) -> PromptVersion | None:
    return session.get(PromptVersion, version_id) if version_id is not None else None


def _latest(session: Session, template_id: UUID) -> PromptVersion | None:
    return session.scalars(
        select(PromptVersion)
        .where(PromptVersion.template_id == template_id)
        .order_by(PromptVersion.version_no.desc())
        .limit(1)
    ).first()


def view_of(session: Session, template: PromptTemplate) -> TemplateView:
    latest = _latest(session, template.id)
    if template.scope == Scope.PERSONAL.value:
        return TemplateView(template, latest, latest, None)
    active = _version(session, template.active_version_id)
    update = None
    if template.scope == Scope.COACHING.value and active is not None:
        platform = _platform_template(session, template.operation)
        if (
            platform is not None
            and platform.active_version_id is not None
            and platform.active_version_id != template.based_on_version_id
        ):
            update = _version(session, platform.active_version_id)
    return TemplateView(template, active, latest, update)


def _may_see(principal: Principal, template: PromptTemplate) -> bool:
    if template.scope != Scope.PERSONAL.value:
        return True
    return template.owner_user_id == principal.user_id or is_allowed(
        principal, Action.MANAGE_AI_SETTINGS
    )


def require_reader(principal: Principal) -> None:
    """Anyone in a coaching may read the library; so may a platform admin (who edits defaults)."""
    if not is_allowed(principal, Action.USE_AI):
        require(principal, Action.MANAGE_PLATFORM_PROMPTS)


def get_template(session: Session, principal: Principal, template_id: UUID) -> PromptTemplate:
    require_reader(principal)
    template = session.get(PromptTemplate, template_id)
    if template is None or not _may_see(principal, template):
        raise NotFound("No such prompt.")
    return template


def list_templates(
    session: Session,
    principal: Principal,
    *,
    operation: Operation | None = None,
    scope: Scope | None = None,
) -> list[TemplateView]:
    """Every prompt the person may see, platform first. A person sees their own personal prompts;
    an admin sees everyone's in the coaching."""
    require_reader(principal)
    organization_id = principal.tenant_context.organization_id
    query = select(PromptTemplate).where(
        (PromptTemplate.organization_id.is_(None))
        | (PromptTemplate.organization_id == organization_id)
    )
    if operation is not None:
        query = query.where(PromptTemplate.operation == operation.value)
    if scope is not None:
        query = query.where(PromptTemplate.scope == scope.value)
    order = {Scope.PLATFORM.value: 0, Scope.COACHING.value: 1, Scope.PERSONAL.value: 2}
    rows = sorted(
        (row for row in session.scalars(query) if _may_see(principal, row)),
        key=lambda row: (order[row.scope], row.operation, row.target_language or "", row.name),
    )
    return [view_of(session, row) for row in rows]


def list_versions(session: Session, principal: Principal, template_id: UUID) -> list[PromptVersion]:
    template = get_template(session, principal, template_id)
    return list(
        session.scalars(
            select(PromptVersion)
            .where(PromptVersion.template_id == template.id)
            .order_by(PromptVersion.version_no.desc())
        )
    )


def get_version(
    session: Session, principal: Principal, version_id: UUID
) -> tuple[PromptVersion, PromptTemplate]:
    require_reader(principal)
    version = session.get(PromptVersion, version_id)
    template = session.get(PromptTemplate, version.template_id) if version is not None else None
    if version is None or template is None or not _may_see(principal, template):
        raise NotFound("No such prompt version.")
    return version, template


# --- Writing ------------------------------------------------------------------------------------


def _actor_is_platform(principal: Principal, scope: Scope) -> bool:
    return principal.acting_organization_id is not None or scope is Scope.PLATFORM


def _audit(
    session: Session,
    principal: Principal,
    template: PromptTemplate,
    action: str,
    *,
    request_id: str | None,
    before: dict[str, object] | None,
    after: dict[str, object] | None,
) -> None:
    record_event(
        session,
        action=action,
        entity_type=ENTITY_TYPE,
        entity_id=template.id,
        organization_id=template.organization_id,
        actor_user_id=principal.user_id,
        actor_is_platform=_actor_is_platform(principal, Scope(template.scope)),
        request_id=request_id,
        before=before,
        after=after,
    )


def _require_may_write(principal: Principal, scope: Scope, template: PromptTemplate | None) -> None:
    if scope is Scope.PLATFORM:
        require(principal, Action.MANAGE_PLATFORM_PROMPTS)
        return
    require(principal, Action.USE_AI)
    if scope is Scope.COACHING:
        if not has_grant(principal, Grant.MANAGE_AI_PROMPTS):
            raise PermissionDenied("You don't have permission to change the coaching's prompts.")
        return
    if template is not None and template.owner_user_id != principal.user_id:
        raise PermissionDenied("This is another person's personal prompt.")


def _own_org(principal: Principal, scope: Scope) -> UUID | None:
    if scope is Scope.PLATFORM:
        return None
    organization_id = principal.tenant_context.organization_id
    if organization_id is None:
        raise PreconditionFailed("Choose a coaching to work in.")
    return organization_id


def _find_template(
    session: Session,
    scope: Scope,
    organization_id: UUID | None,
    owner_user_id: UUID | None,
    operation: Operation,
    target_language: str | None,
    name: str | None,
) -> PromptTemplate | None:
    query = select(PromptTemplate).where(
        PromptTemplate.scope == scope.value, PromptTemplate.operation == operation.value
    )
    if scope is Scope.PLATFORM:
        pass
    elif scope is Scope.COACHING:
        query = query.where(PromptTemplate.organization_id == organization_id)
        query = query.where(
            PromptTemplate.target_language.is_(None)
            if target_language is None
            else PromptTemplate.target_language == target_language
        )
    else:
        query = query.where(
            PromptTemplate.organization_id == organization_id,
            PromptTemplate.owner_user_id == owner_user_id,
            func.lower(PromptTemplate.name) == (name or "").lower(),
        )
    return session.scalars(query).first()


def create_version(
    session: Session,
    principal: Principal,
    *,
    scope: Scope,
    operation: Operation,
    instructions: str,
    temperature: Decimal | None,
    change_note: str,
    template_id: UUID | None = None,
    name: str | None = None,
    target_language: str | None = None,
    request_id: str | None,
) -> tuple[PromptTemplate, PromptVersion]:
    """Save instructions as a new version (never active yet; activating is its own step).

    Give ``template_id`` to add to an existing prompt. Otherwise the prompt for this scope and
    operation (and translation language, or personal name) is found or started.
    """
    template: PromptTemplate | None = None
    if template_id is not None:
        existing = get_template(session, principal, template_id)
        template = existing
        scope = Scope(existing.scope)
        operation = Operation(existing.operation)
    _require_may_write(principal, scope, template)
    require_valid(operation, instructions)
    note = change_note.strip()
    if not note:
        raise ValidationFailed("Say what you changed.", code="AI_PROMPT_NOTE_REQUIRED")
    if target_language is not None and (
        operation is not Operation.TRANSLATE or target_language not in language_names()
    ):
        raise ValidationFailed(
            "A language applies only to translation, and must be one of the question languages.",
            code="AI_PROMPT_LANGUAGE_INVALID",
        )
    organization_id = _own_org(principal, scope)

    if template is None:
        if scope is Scope.PERSONAL and not (name and name.strip()):
            raise ValidationFailed("Give your prompt a name.", code="AI_PROMPT_NAME_REQUIRED")
        display = (name or "").strip() or f"{operation.value.title()} prompt"
        owner = principal.user_id if scope is Scope.PERSONAL else None
        template = _find_template(
            session, scope, organization_id, owner, operation, target_language, display
        )
        if template is None:
            platform = _platform_template(session, operation.value)
            template = PromptTemplate(
                organization_id=organization_id,
                scope=scope.value,
                operation=operation.value,
                owner_user_id=owner,
                name=display[:100],
                target_language=target_language,
                based_on_version_id=(
                    platform.active_version_id
                    if scope is Scope.COACHING and platform is not None
                    else None
                ),
                created_by=principal.user_id,
            )
            try:
                with session.begin_nested():
                    session.add(template)
                    session.flush()
            except IntegrityError:  # someone started the same prompt at the same moment
                template = _find_template(
                    session, scope, organization_id, owner, operation, target_language, display
                )
                if template is None:
                    raise
    locked_row = session.scalars(
        select(PromptTemplate).where(PromptTemplate.id == template.id).with_for_update()
    ).one()
    latest = _latest(session, locked_row.id)
    version = PromptVersion(
        organization_id=locked_row.organization_id,
        template_id=locked_row.id,
        version_no=(latest.version_no if latest is not None else 0) + 1,
        instructions=instructions,
        temperature=temperature,
        change_note=note,
        author_id=principal.user_id,
        content_hash=content_hash(instructions, temperature),
    )
    session.add(version)
    session.flush()
    _audit(
        session,
        principal,
        locked_row,
        "AI_PROMPT_VERSION_SAVED",
        request_id=request_id,
        before=None,
        after={
            "scope": locked_row.scope,
            "operation": locked_row.operation,
            "version_no": version.version_no,
            "change_note": note,
            "content_hash": version.content_hash,
        },
    )
    return locked_row, version


def _switch(
    session: Session,
    principal: Principal,
    template: PromptTemplate,
    version: PromptVersion | None,
    action: str,
) -> None:
    template.active_version_id = version.id if version is not None else None
    template.revision += 1
    session.add(
        PromptActivation(
            organization_id=template.organization_id,
            template_id=template.id,
            version_id=version.id if version is not None else None,
            action=action,
            activated_by=principal.user_id,
        )
    )
    session.flush()


def _lock_for_switch(
    session: Session, principal: Principal, template_id: UUID, if_match: str | None
) -> PromptTemplate:
    template = get_template(session, principal, template_id)
    scope = Scope(template.scope)
    if scope is Scope.PERSONAL:
        raise Conflict(
            "A personal prompt has no active version: pick it when you run.",
            code="AI_PROMPT_PERSONAL_NOT_ACTIVATED",
        )
    _require_may_write(principal, scope, template)
    locked_row = session.scalars(
        select(PromptTemplate).where(PromptTemplate.id == template_id).with_for_update()
    ).one()
    require_if_match(if_match, locked_row.revision)
    return locked_row


def _tell_admins(
    session: Session, principal: Principal, template: PromptTemplate, version: PromptVersion
) -> None:
    if template.organization_id is None:
        return
    for user_id in admin_user_ids(session, template.organization_id):
        if user_id != principal.user_id:
            notify(
                session,
                organization_id=template.organization_id,
                user_id=user_id,
                kind="AI_PROMPT_ACTIVATED",
                data={
                    "template_id": str(template.id),
                    "operation": template.operation,
                    "version_no": version.version_no,
                },
            )


def activate(
    session: Session,
    principal: Principal,
    template_id: UUID,
    version_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
) -> TemplateView:
    """Make a saved version the one in use. An older version than the current one is a rollback.
    The previous version stays; the coaching's admins get an in-app notice."""
    template = _lock_for_switch(session, principal, template_id, if_match)
    version = session.get(PromptVersion, version_id)
    if version is None or version.template_id != template.id:
        raise NotFound("That version does not belong to this prompt.")
    current = _version(session, template.active_version_id)
    if current is not None and current.id == version.id:
        return view_of(session, template)  # already in use: nothing to switch
    rollback = current is not None and version.version_no < current.version_no
    _switch(session, principal, template, version, "ROLLBACK" if rollback else "ACTIVATE")
    _audit(
        session,
        principal,
        template,
        "AI_PROMPT_ROLLED_BACK" if rollback else "AI_PROMPT_ACTIVATED",
        request_id=request_id,
        before={"version_no": current.version_no if current is not None else None},
        after={"version_no": version.version_no},
    )
    _tell_admins(session, principal, template, version)
    return view_of(session, template)


def reset(
    session: Session,
    principal: Principal,
    template_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
) -> TemplateView:
    """Remove the coaching's override: the next run uses the platform default again (PL-09)."""
    template = _lock_for_switch(session, principal, template_id, if_match)
    if template.scope != Scope.COACHING.value:
        raise Conflict(
            "Only a coaching's own prompt can be reset.", code="AI_PROMPT_NOT_RESETTABLE"
        )
    current = _version(session, template.active_version_id)
    if current is None:
        return view_of(session, template)
    platform = _platform_template(session, template.operation)
    template.based_on_version_id = platform.active_version_id if platform is not None else None
    _switch(session, principal, template, None, "RESET")
    _audit(
        session,
        principal,
        template,
        "AI_PROMPT_RESET",
        request_id=request_id,
        before={"version_no": current.version_no},
        after={"version_no": None},
    )
    return view_of(session, template)


def _newer_platform_default(
    session: Session, template: PromptTemplate
) -> tuple[PromptTemplate, PromptVersion]:
    platform = _platform_template(session, template.operation)
    newer = _version(session, platform.active_version_id) if platform is not None else None
    if (
        template.scope != Scope.COACHING.value
        or template.active_version_id is None
        or platform is None
        or newer is None
        or newer.id == template.based_on_version_id
    ):
        raise Conflict("There is no newer platform default to look at.", code="AI_PROMPT_NO_UPDATE")
    return platform, newer


def adopt_default(
    session: Session,
    principal: Principal,
    template_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
) -> TemplateView:
    """Take the platform's newer default as the coaching's own: a new version with its text, made
    active (PL-10). The coaching's earlier versions stay."""
    template = _lock_for_switch(session, principal, template_id, if_match)
    _, newer = _newer_platform_default(session, template)
    latest = _latest(session, template.id)
    version = PromptVersion(
        organization_id=template.organization_id,
        template_id=template.id,
        version_no=(latest.version_no if latest is not None else 0) + 1,
        instructions=newer.instructions,
        temperature=newer.temperature,
        change_note=f"Adopted platform default version {newer.version_no}"[:300],
        author_id=principal.user_id,
        content_hash=newer.content_hash,
    )
    session.add(version)
    session.flush()
    before = _version(session, template.active_version_id)
    template.based_on_version_id = newer.id
    _switch(session, principal, template, version, "ADOPT_DEFAULT")
    _audit(
        session,
        principal,
        template,
        "AI_PROMPT_DEFAULT_ADOPTED",
        request_id=request_id,
        before={"version_no": before.version_no if before is not None else None},
        after={"version_no": version.version_no, "platform_version_no": newer.version_no},
    )
    _tell_admins(session, principal, template, version)
    return view_of(session, template)


def dismiss_update(
    session: Session,
    principal: Principal,
    template_id: UUID,
    *,
    if_match: str | None,
    request_id: str | None,
) -> TemplateView:
    """Keep the coaching's own prompt and stop showing this newer platform default."""
    template = _lock_for_switch(session, principal, template_id, if_match)
    _, newer = _newer_platform_default(session, template)
    template.based_on_version_id = newer.id
    template.revision += 1
    session.flush()
    _audit(
        session,
        principal,
        template,
        "AI_PROMPT_UPDATE_DISMISSED",
        request_id=request_id,
        before=None,
        after={"platform_version_no": newer.version_no},
    )
    return view_of(session, template)


# --- Comparing ------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DiffLine:
    op: Literal["same", "removed", "added"]
    text: str


@dataclass(frozen=True, slots=True)
class VersionDiff:
    lines: list[DiffLine]
    temperature_from: Decimal | None
    temperature_to: Decimal | None
    changed: bool


def diff(session: Session, principal: Principal, from_id: UUID, to_id: UUID) -> VersionDiff:
    """Line by line, what changed from one version to another of the same operation (PL-08)."""
    before, before_template = get_version(session, principal, from_id)
    after, after_template = get_version(session, principal, to_id)
    if before_template.operation != after_template.operation:
        raise ValidationFailed(
            "Only versions of the same operation can be compared.", code="AI_PROMPT_DIFF_MISMATCH"
        )
    a, b = before.instructions.splitlines(), after.instructions.splitlines()
    lines: list[DiffLine] = []
    for tag, a1, a2, b1, b2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            lines.extend(DiffLine("same", text) for text in a[a1:a2])
            continue
        lines.extend(DiffLine("removed", text) for text in a[a1:a2])
        lines.extend(DiffLine("added", text) for text in b[b1:b2])
    changed = any(line.op != "same" for line in lines) or before.temperature != after.temperature
    return VersionDiff(lines, before.temperature, after.temperature, changed)


# --- Choosing a prompt for a run ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Resolved:
    """The prompt a run will use, as the run records it."""

    source: Literal["PERSONAL", "COACHING", "PLATFORM", "ONE_OFF"]
    version_id: UUID | None  # None for a one-off prompt: its text is kept on the run only
    instructions: str
    temperature: Decimal | None
    content_hash: str


def _resolved(source: Literal["PERSONAL", "COACHING", "PLATFORM"], v: PromptVersion) -> Resolved:
    return Resolved(source, v.id, v.instructions, v.temperature, v.content_hash)


def resolve(
    session: Session,
    *,
    organization_id: UUID,
    user_id: UUID,
    operation: Operation,
    language: str | None = None,
    personal_template_id: UUID | None = None,
    one_off: str | None = None,
) -> Resolved:
    """The prompt for a run: a one-off text typed for this run (checked like any prompt, stored
    nowhere but on the run), one of the person's own prompts (its latest version), or the default:
    the coaching's active prompt (for the translation language if it has one for it), else the
    platform's."""
    if one_off is not None:
        require_valid(operation, one_off)
        return Resolved("ONE_OFF", None, one_off, None, content_hash(one_off, None))
    if personal_template_id is not None:
        template = session.get(PromptTemplate, personal_template_id)
        if (
            template is None
            or template.scope != Scope.PERSONAL.value
            or template.organization_id != organization_id
            or template.owner_user_id != user_id
            or template.operation != operation.value
        ):
            raise NotFound("No such personal prompt.")
        latest = _latest(session, template.id)
        if latest is None:
            raise NotFound("This personal prompt has no saved version yet.")
        return _resolved("PERSONAL", latest)
    wanted: list[str | None] = [language, None] if language else [None]
    for target_language in wanted:
        query = select(PromptTemplate).where(
            PromptTemplate.scope == Scope.COACHING.value,
            PromptTemplate.organization_id == organization_id,
            PromptTemplate.operation == operation.value,
            PromptTemplate.active_version_id.is_not(None),
        )
        query = query.where(
            PromptTemplate.target_language.is_(None)
            if target_language is None
            else PromptTemplate.target_language == target_language
        )
        coaching = session.scalars(query).first()
        version = _version(session, coaching.active_version_id) if coaching is not None else None
        if version is not None:
            return _resolved("COACHING", version)
    platform = _platform_template(session, operation.value)
    version = _version(session, platform.active_version_id) if platform is not None else None
    if version is None:
        raise NotFound("There is no default prompt for this operation.")
    return _resolved("PLATFORM", version)
