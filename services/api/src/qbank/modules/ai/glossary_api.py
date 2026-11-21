"""Routes for the translation glossary (M5 design note §10; H-14)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader
from qbank.modules.ai import glossary
from qbank.modules.ai.models import GlossaryEntry
from qbank.modules.ai.schemas import (
    AddGlossaryEntry,
    ChangeGlossaryEntry,
    GlossaryEntryOut,
    GlossaryOut,
)

router = APIRouter(prefix="/api/v1/ai/glossary", tags=["ai"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Only the Owner and admins (`PERMISSION_DENIED`)"}
}
_CHANGE: dict[int | str, dict[str, Any]] = {
    **_DENIED,
    404: {"description": "No such entry (`NOT_FOUND`)"},
    412: {"description": "Changed since you read it (`REVISION_STALE`)"},
    428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
}


def _out(entry: GlossaryEntry) -> GlossaryEntryOut:
    return GlossaryEntryOut(
        id=entry.id,
        language=entry.language,
        source_term=entry.source_term,
        target_term=entry.target_term,
        note=entry.note,
        revision=entry.revision,
        updated_at=entry.updated_at,
    )


@router.get(
    "",
    summary="The coaching translation glossary (H-14)",
    description="Owner and admins. Terms the coaching wants translated one fixed way, per target"
    " language. A translation run is given the entries whose source term appears in the question.",
    responses=_DENIED,
)
def list_glossary(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    language: str | None = None,
) -> GlossaryOut:
    with database.transaction(principal.tenant_context) as session:
        rows = glossary.list_entries(session, principal, language=language)
        return GlossaryOut(data=[_out(row) for row in rows])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a term (H-14)",
    description="Owner and admins. A term has one entry per language, ignoring case. Written to"
    " the audit log.",
    responses={
        **_DENIED,
        409: {
            "description": "The term already has an entry (`AI_GLOSSARY_DUPLICATE`), or the"
            " language is full (`AI_GLOSSARY_FULL`)"
        },
        422: {"description": "Not a question language, or an empty term"},
    },
)
def add_term(
    body: AddGlossaryEntry,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> GlossaryEntryOut:
    with database.transaction(principal.tenant_context) as session:
        entry = glossary.create_entry(
            session,
            principal,
            language=body.language,
            source_term=body.source_term,
            target_term=body.target_term,
            note=body.note,
            request_id=request.state.request_id,
        )
        result = _out(entry)
    response.headers["ETag"] = f'"rev-{result.revision}"'
    return result


@router.put(
    "/{entry_id}",
    summary="Change a term (H-14)",
    description="Owner and admins. Replaces the terms and note of an entry; its language stays."
    " Send the entry `revision` as the ETag. Written to the audit log.",
    responses={**_CHANGE, 409: {"description": "The new term clashes (`AI_GLOSSARY_DUPLICATE`)"}},
)
def change_term(
    entry_id: UUID,
    body: ChangeGlossaryEntry,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> GlossaryEntryOut:
    with database.transaction(principal.tenant_context) as session:
        entry = glossary.update_entry(
            session,
            principal,
            entry_id,
            source_term=body.source_term,
            target_term=body.target_term,
            note=body.note,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _out(entry)
    response.headers["ETag"] = f'"rev-{result.revision}"'
    return result


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a term (H-14)",
    description="Owner and admins. Send the entry `revision` as the ETag. Written to the audit"
    " log.",
    responses=_CHANGE,
)
def remove_term(
    entry_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> Response:
    with database.transaction(principal.tenant_context) as session:
        glossary.delete_entry(
            session,
            principal,
            entry_id,
            if_match=if_match,
            request_id=request.state.request_id,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
