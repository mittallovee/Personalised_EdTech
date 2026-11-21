"""Routes for the prompt library (M5 design note §10; prompt spec PL-01 to PL-10)."""

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.modules.ai import locked, prompts
from qbank.modules.ai.models import PromptTemplate, PromptVersion
from qbank.modules.ai.names import Operation, Scope
from qbank.modules.ai.schemas import (
    ActivateIn,
    DiffLineOut,
    DiffOut,
    LockedOut,
    LockedPartsOut,
    ProblemOut,
    SavedVersion,
    SaveVersion,
    TemplateOut,
    TemplatesOut,
    ValidateIn,
    ValidateOut,
    VersionOut,
    VersionsOut,
    VersionSummary,
)
from qbank.modules.identity.public import display_names

router = APIRouter(prefix="/api/v1/ai/prompts", tags=["ai"])

_STALE: dict[int | str, dict[str, Any]] = {
    403: {
        "description": "No right to change this prompt (`PERMISSION_DENIED`): the coaching's"
        " prompts need the `MANAGE_AI_PROMPTS` grant, the platform's a platform admin"
    },
    404: {"description": "No such prompt (`NOT_FOUND`)"},
    412: {"description": "Changed since you read it (`REVISION_STALE`)"},
    428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
}


def _temperature(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")


def _summary(version: PromptVersion, names: dict[UUID, str]) -> VersionSummary:
    return VersionSummary(
        id=version.id,
        version_no=version.version_no,
        change_note=version.change_note,
        author_id=version.author_id,
        author_name=names.get(version.author_id) if version.author_id is not None else None,
        created_at=version.created_at,
        temperature=_temperature(version.temperature),
        content_hash=version.content_hash,
    )


def _template_out(view: prompts.TemplateView, names: dict[UUID, str]) -> TemplateOut:
    template = view.template
    return TemplateOut(
        id=template.id,
        scope=Scope(template.scope),
        operation=Operation(template.operation),
        name=template.name,
        target_language=template.target_language,
        owner_user_id=template.owner_user_id,
        revision=template.revision,
        active_version=_summary(view.active, names) if view.active is not None else None,
        latest_version=_summary(view.latest, names) if view.latest is not None else None,
        update_available=(
            _summary(view.update_available, names) if view.update_available is not None else None
        ),
    )


def _authors(views: list[prompts.TemplateView]) -> list[UUID]:
    found: set[UUID] = set()
    for view in views:
        for version in (view.active, view.latest, view.update_available):
            if version is not None and version.author_id is not None:
                found.add(version.author_id)
    return list(found)


def _one(session: Any, view: prompts.TemplateView) -> TemplateOut:
    return _template_out(view, display_names(session, _authors([view])))


@router.get(
    "/locked",
    summary="The parts of a prompt nobody can edit (PL-02)",
    description="Any member. The safety preamble every prompt is sent with, and for each operation"
    " the placeholders its instructions may (and must) use. The output format is fixed by the"
    " system too, so a prompt edit cannot break how the answer is read.",
)
def locked_parts(principal: CurrentPrincipal) -> LockedOut:
    prompts.require_reader(principal)
    return LockedOut(
        data=[
            LockedPartsOut(
                operation=operation,
                safety_preamble=locked.SAFETY_PREAMBLE,
                required_placeholders=sorted(rules.required),
                optional_placeholders=sorted(rules.optional),
                max_instruction_chars=locked.MOST_INSTRUCTION_CHARS,
            )
            for operation, rules in locked.PLACEHOLDERS.items()
        ]
    )


@router.get(
    "",
    summary="The prompts you can see, with the version in use (PL-01)",
    description="Platform defaults, the coaching's prompts and your own personal prompts (admins"
    " also see everyone's personal prompts). For a coaching prompt, `update_available` is set when"
    " the platform has a newer default than the one it was based on (PL-10).",
)
def list_prompts(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    operation: Operation | None = None,
    scope: Scope | None = None,
) -> TemplatesOut:
    with database.transaction(principal.tenant_context) as session:
        views = prompts.list_templates(session, principal, operation=operation, scope=scope)
        names = display_names(session, _authors(views))
        return TemplatesOut(data=[_template_out(view, names) for view in views])


@router.post(
    "/validate",
    summary="Check instructions without saving them (PL-05)",
    description="Any member. Lists every problem at once: an unknown placeholder, a missing"
    " required one, too long, or something that looks like a key. Saving runs the same check.",
)
def validate(body: ValidateIn, principal: CurrentPrincipal) -> ValidateOut:
    prompts.require_reader(principal)
    problems = prompts.check_instructions(body.operation, body.instructions)
    return ValidateOut(
        ok=not problems,
        problems=[ProblemOut(code=p.code, message=p.message) for p in problems],
    )


@router.get(
    "/diff",
    summary="What changed between two versions (PL-08)",
    description="Any member, for versions they can see. Line by line; the two must be versions of"
    " the same operation.",
    responses={404: {"description": "No such version (`NOT_FOUND`)"}},
)
def compare(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    from_version: Annotated[UUID, Query(alias="from")],
    to_version: Annotated[UUID, Query(alias="to")],
) -> DiffOut:
    with database.transaction(principal.tenant_context) as session:
        result = prompts.diff(session, principal, from_version, to_version)
    return DiffOut(
        changed=result.changed,
        lines=[DiffLineOut(op=line.op, text=line.text) for line in result.lines],
        temperature_from=_temperature(result.temperature_from),
        temperature_to=_temperature(result.temperature_to),
    )


@router.get(
    "/templates/{template_id}",
    summary="One prompt, with its ETag (PL-01)",
    responses={404: {"description": "No such prompt (`NOT_FOUND`)"}},
)
def get_template(
    template_id: UUID,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> TemplateOut:
    with database.transaction(principal.tenant_context) as session:
        template = prompts.get_template(session, principal, template_id)
        result = _one(session, prompts.view_of(session, template))
    response.headers["ETag"] = etag(result.revision)
    return result


@router.get(
    "/templates/{template_id}/versions",
    summary="Every saved version of a prompt, newest first (PL-03)",
    responses={404: {"description": "No such prompt (`NOT_FOUND`)"}},
)
def list_versions(
    template_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> VersionsOut:
    with database.transaction(principal.tenant_context) as session:
        versions = prompts.list_versions(session, principal, template_id)
        names = display_names(session, [v.author_id for v in versions if v.author_id is not None])
        return VersionsOut(data=[_summary(version, names) for version in versions])


@router.get(
    "/versions/{version_id}",
    summary="One saved version with its full text (PL-02)",
    responses={404: {"description": "No such version (`NOT_FOUND`)"}},
)
def get_version(
    version_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> VersionOut:
    with database.transaction(principal.tenant_context) as session:
        version, template = prompts.get_version(session, principal, version_id)
        names = display_names(session, [version.author_id] if version.author_id else [])
        return _version_out(version, template, names)


def _version_out(
    version: PromptVersion, template: PromptTemplate, names: dict[UUID, str]
) -> VersionOut:
    return VersionOut(
        **_summary(version, names).model_dump(),
        template_id=template.id,
        instructions=version.instructions,
        operation=Operation(template.operation),
        scope=Scope(template.scope),
        is_active=template.active_version_id == version.id,
    )


@router.post(
    "/versions",
    status_code=status.HTTP_201_CREATED,
    summary="Save instructions as a new version (PL-03, PL-04, PL-05)",
    description="Saves a new version; it is **not** used until activated. A change note is"
    " required. Personal prompts need a `name` the first time. The coaching's prompts need the"
    " `MANAGE_AI_PROMPTS` grant; the platform's need a platform admin. Written to the audit log.",
    responses={
        403: _STALE[403],
        422: {
            "description": "The instructions cannot be used (`AI_PROMPT_INVALID`, with every"
            " problem in `details.problems`), or a note, name or language is wrong"
        },
    },
)
def save_version(
    body: SaveVersion,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> SavedVersion:
    with database.transaction(principal.tenant_context) as session:
        template, version = prompts.create_version(
            session,
            principal,
            scope=body.scope,
            operation=body.operation,
            instructions=body.instructions,
            temperature=body.temperature,
            change_note=body.change_note,
            template_id=body.template_id,
            name=body.name,
            target_language=body.target_language,
            request_id=request.state.request_id,
        )
        names = display_names(session, [principal.user_id])
        return SavedVersion(
            template=_one(session, prompts.view_of(session, template)),
            version=_version_out(version, template, names),
        )


@router.post(
    "/templates/{template_id}/activate",
    summary="Use a saved version, or go back to an older one (PL-07, PL-09)",
    description="The coaching's prompts need the `MANAGE_AI_PROMPTS` grant. An older version than"
    " the current one is a rollback. The previous version is kept and the coaching's admins get an"
    " in-app notice. Send the prompt's `revision` as the ETag. A personal prompt is not activated:"
    " it is picked when you run.",
    responses={
        **_STALE,
        409: {"description": "A personal prompt (`AI_PROMPT_PERSONAL_NOT_ACTIVATED`)"},
    },
)
def activate(
    template_id: UUID,
    body: ActivateIn,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> TemplateOut:
    with database.transaction(principal.tenant_context) as session:
        view = prompts.activate(
            session,
            principal,
            template_id,
            body.version_id,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _one(session, view)
    response.headers["ETag"] = etag(result.revision)
    return result


@router.post(
    "/templates/{template_id}/reset",
    summary="Remove the coaching's override and use the platform default (PL-09)",
    description="The coaching's prompt keeps its versions but stops being used. Send the prompt's"
    " `revision` as the ETag.",
    responses={
        **_STALE,
        409: {"description": "Not a coaching prompt (`AI_PROMPT_NOT_RESETTABLE`)"},
    },
)
def reset(
    template_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> TemplateOut:
    with database.transaction(principal.tenant_context) as session:
        view = prompts.reset(
            session,
            principal,
            template_id,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _one(session, view)
    response.headers["ETag"] = etag(result.revision)
    return result


@router.post(
    "/templates/{template_id}/adopt-default",
    summary="Take the platform's newer default as the coaching's own (PL-10)",
    description="Saves the platform's newer default as a new version of the coaching's prompt and"
    " activates it. Send the prompt's `revision` as the ETag.",
    responses={**_STALE, 409: {"description": "No newer platform default (`AI_PROMPT_NO_UPDATE`)"}},
)
def adopt_default(
    template_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> TemplateOut:
    with database.transaction(principal.tenant_context) as session:
        view = prompts.adopt_default(
            session,
            principal,
            template_id,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _one(session, view)
    response.headers["ETag"] = etag(result.revision)
    return result


@router.post(
    "/templates/{template_id}/dismiss-update",
    summary="Keep the coaching's own prompt and stop showing the newer default (PL-10)",
    responses={**_STALE, 409: {"description": "No newer platform default (`AI_PROMPT_NO_UPDATE`)"}},
)
def dismiss_update(
    template_id: UUID,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> TemplateOut:
    with database.transaction(principal.tenant_context) as session:
        view = prompts.dismiss_update(
            session,
            principal,
            template_id,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _one(session, view)
    response.headers["ETag"] = etag(result.revision)
    return result
