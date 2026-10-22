from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, PageInfo
from qbank.core.permissions import Action, require
from qbank.modules.taxonomy import service
from qbank.modules.taxonomy.catalogues import BLOOM_LEVELS, DIFFICULTY_GUIDE, LANGUAGES
from qbank.modules.taxonomy.schemas import (
    BloomLevelOut,
    CreateNode,
    DifficultyLevelOut,
    LanguageOut,
    NodeKind,
    NodeOut,
    NodePage,
    NodeState,
    UpdateNode,
)

catalogues = APIRouter(prefix="/api/v1", tags=["catalogues"])
router = APIRouter(prefix="/api/v1/taxonomy/nodes", tags=["taxonomy"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such item in your coaching (`NOT_FOUND`)"}
}
_STALE: dict[int | str, dict[str, Any]] = {
    412: {"description": "Changed by someone else since you read it (`REVISION_STALE`)"},
    428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
}


@catalogues.get(
    "/languages",
    summary="The question languages",
    description="The same for every coaching. English comes first.",
)
def list_languages(_principal: CurrentPrincipal) -> list[LanguageOut]:
    return [
        LanguageOut(
            tag=language.tag,
            english_name=language.english_name,
            native_name=language.native_name,
        )
        for language in LANGUAGES
    ]


@catalogues.get("/catalogues/bloom", summary="The Bloom levels, easiest first")
def list_bloom_levels(_principal: CurrentPrincipal) -> list[BloomLevelOut]:
    return [BloomLevelOut(key=level.key, label=level.label) for level in BLOOM_LEVELS]


@catalogues.get(
    "/catalogues/difficulty-guide",
    summary="What each difficulty level from 1 to 10 means",
    description="Shown beside the difficulty field of the question editor.",
)
def difficulty_guide(_principal: CurrentPrincipal) -> list[DifficultyLevelOut]:
    return [DifficultyLevelOut(level=item.level, meaning=item.meaning) for item in DIFFICULTY_GUIDE]


@router.get(
    "",
    summary="Syllabus items, in the admin's order",
    description=(
        "Everyone in the coaching can read them. Filter by `kind` and by `parent_id` (the items"
        " directly under one item). Retired items are included unless you ask for `state=ACTIVE`,"
        " which is what a picker for a new question should do."
    ),
    responses=_DENIED,
)
def list_nodes(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    kind: NodeKind | None = None,
    parent_id: UUID | None = None,
    node_state: Annotated[NodeState | None, Query(alias="state")] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query(max_length=300)] = None,
) -> NodePage:
    require(principal, Action.VIEW_CATALOGUES)
    after = service.decode_position(cursor) if cursor is not None else None
    with database.transaction(principal.tenant_context) as session:
        rows, has_more = service.list_nodes(
            session, kind=kind, parent_id=parent_id, state=node_state, limit=limit, after=after
        )
        data = service.describe(session, rows)
    return NodePage(
        data=data,
        page=PageInfo(next_cursor=service.next_cursor(rows, has_more), has_more=has_more),
    )


@router.get(
    "/{node_id}",
    summary="One syllabus item",
    description="The ETag is its revision, for changes that need `If-Match`.",
    responses={**_DENIED, **_NOT_FOUND},
)
def get_node(
    node_id: UUID,
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> NodeOut:
    require(principal, Action.VIEW_CATALOGUES)
    with database.transaction(principal.tenant_context) as session:
        node = service.get_node(session, node_id)
        response.headers["ETag"] = etag(node.revision)
        return service.describe(session, [node])[0]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a syllabus item",
    description=(
        "Owner and admins. A subject goes under a class, a chapter under a subject, a topic under"
        " a chapter and a subtopic under a topic; a class has no parent."
    ),
    responses={
        **_DENIED,
        **_NOT_FOUND,
        409: {
            "description": "A sibling has this name (`DUPLICATE_NAME`) or the parent is retired"
            " (`PARENT_DEPRECATED`)"
        },
        422: {"description": "Wrong kind of parent (`HIERARCHY_INVALID`)"},
    },
)
def create_node(
    body: CreateNode,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> NodeOut:
    require(principal, Action.MANAGE_CATALOGUES)
    with database.transaction(principal.tenant_context) as session:
        node = service.create_node(session, principal, body, request_id=request.state.request_id)
        result = service.describe(session, [node])[0]
        response.headers["ETag"] = etag(node.revision)
    response.headers["Location"] = f"/api/v1/taxonomy/nodes/{result.id}"
    return result


@router.patch(
    "/{node_id}",
    summary="Rename, reorder or translate a syllabus item",
    description="Send the ETag you last read in `If-Match`. The kind and parent never change.",
    responses={
        **_DENIED,
        **_NOT_FOUND,
        **_STALE,
        409: {"description": "A sibling has this name (`DUPLICATE_NAME`)"},
    },
)
def update_node(
    node_id: UUID,
    body: UpdateNode,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> NodeOut:
    require(principal, Action.MANAGE_CATALOGUES)
    with database.transaction(principal.tenant_context) as session:
        node = service.update_node(
            session,
            principal,
            node_id,
            body,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(node.revision)
        return service.describe(session, [node])[0]


def _set_state(
    node_id: UUID,
    node_state: str,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Database,
    if_match: str | None,
) -> NodeOut:
    require(principal, Action.MANAGE_CATALOGUES)
    with database.transaction(principal.tenant_context) as session:
        node = service.set_state(
            session,
            principal,
            node_id,
            node_state,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        response.headers["ETag"] = etag(node.revision)
        return service.describe(session, [node])[0]


@router.post(
    "/{node_id}/deprecate",
    summary="Retire a syllabus item",
    description=(
        "It can no longer be chosen for new questions; questions that already use it keep it."
        " Items under it are not changed."
    ),
    responses={**_DENIED, **_NOT_FOUND, **_STALE},
)
def deprecate_node(
    node_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> NodeOut:
    return _set_state(node_id, "DEPRECATED", principal, request, response, database, if_match)


@router.post(
    "/{node_id}/restore",
    summary="Bring a retired syllabus item back",
    responses={
        **_DENIED,
        **_NOT_FOUND,
        **_STALE,
        409: {"description": "Its parent is retired; restore that first (`PARENT_DEPRECATED`)"},
    },
)
def restore_node(
    node_id: UUID,
    principal: CurrentPrincipal,
    request: Request,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> NodeOut:
    return _set_state(node_id, "ACTIVE", principal, request, response, database, if_match)
