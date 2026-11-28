"""Routes for reading documents with AI and deciding what was found (M6 6f/6g, G-04, G-06).

AI only ever proposes: every candidate waits for a person, and accepting one makes a new **draft**
question that goes through the normal review like any other (nothing here submits or publishes).
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.core.permissions import Action, require
from qbank.modules.ingestion import candidates
from qbank.modules.ingestion.models import IngestCandidate, IngestRun
from qbank.modules.ingestion.schemas import (
    CandidateOut,
    CandidatesOut,
    DuplicateOut,
    DuplicatesOut,
    EditCandidate,
    IngestSettingsOut,
    RejectCandidate,
    RunsOut,
    SameAs,
    SaveIngestSettings,
    StartedRun,
    State,
)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Your role may not do this (`PERMISSION_DENIED`)"}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "No such document or candidate of yours (`NOT_FOUND`)"}
}
_DECIDED: dict[int | str, dict[str, Any]] = {
    409: {"description": "Already decided (`INGEST_CANDIDATE_DECIDED`)"},
    412: {"description": "Out of date: reload and try again (`REVISION_STALE`)"},
}


def _rid(request: Request) -> str | None:
    value: str | None = getattr(request.state, "request_id", None)
    return value


def _run(row: IngestRun) -> StartedRun:
    return StartedRun.model_validate(
        {
            "id": row.id,
            "file_id": row.file_id,
            "state": row.state,
            "pages_total": row.pages_total,
            "pages_done": row.pages_done,
            "pages_failed": row.pages_failed,
            "prompt_version": row.prompt_version,
            "error_code": row.error_code,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
        }
    )


def _candidate(row: IngestCandidate) -> CandidateOut:
    return CandidateOut.model_validate(
        {
            "id": row.id,
            "file_id": row.file_id,
            "run_id": row.run_id,
            "page_no": row.page_no,
            "ordinal": row.ordinal,
            "region": row.region,
            "content": row.content,
            "raw": row.raw,
            "findings": row.findings,
            "confidence": row.confidence,
            "warnings": row.warnings,
            "state": row.state,
            "question_id": row.question_id,
            "reject_reason": row.reject_reason,
            "revision": row.revision,
        }
    )


# --- Settings ---------------------------------------------------------------------------------


@router.get(
    "/settings",
    summary="The model documents are read with",
    description="Owner and admins.",
    responses=_DENIED,
)
def read_settings(
    principal: CurrentPrincipal,
    response: Response,
    database: Annotated[Database, Depends(get_database)],
) -> IngestSettingsOut:
    with database.transaction(principal.tenant_context) as session:
        row = candidates.get_settings(session, principal)
        out = IngestSettingsOut(
            model_id=row.model_id if row else None, revision=row.revision if row else 0
        )
    response.headers["ETag"] = etag(out.revision)
    return out


@router.put(
    "/settings",
    summary="Choose the model documents are read with",
    description=(
        "Owner and admins. The model must be enabled, able to answer in the structured form and"
        " known to read pictures (`AI_MODEL_NO_VISION` otherwise). Send the `revision` as the ETag"
        ' (`"rev-0"` when none was saved yet). `null` clears the choice.'
    ),
    responses={**_DENIED, 412: {"description": "Out of date (`REVISION_STALE`)"}},
)
def write_settings(
    body: SaveIngestSettings,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> IngestSettingsOut:
    with database.transaction(principal.tenant_context) as session:
        row = candidates.save_settings(
            session, principal, body.model_id, if_match=if_match, request_id=_rid(request)
        )
        out = IngestSettingsOut(model_id=row.model_id, revision=row.revision)
    response.headers["ETag"] = etag(out.revision)
    return out


# --- Reading a file ---------------------------------------------------------------------------


@router.post(
    "/files/{file_id}/extract",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Read a document's pages with AI (G-04)",
    description=(
        "Same visibility as the file. The pages are read one at a time by the model chosen in the"
        " uploads settings, in the background; each page reserves its cost against the person's"
        " AI budget first. Questions found appear as candidates, never as questions. Refused when"
        " no model is chosen (`INGEST_NO_MODEL`) or the file is not ready or is already being"
        " read (`INGEST_NOT_READY`)."
    ),
    responses={**_DENIED, **_NOT_FOUND, 409: {"description": "Not ready, or no model chosen"}},
)
def extract_file(
    file_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> StartedRun:
    with database.transaction(principal.tenant_context) as session:
        return _run(candidates.start_run(session, principal, file_id, request_id=_rid(request)))


@router.get(
    "/files/{file_id}/runs",
    summary="The readings of a document, newest first",
    responses={**_DENIED, **_NOT_FOUND},
)
def read_runs(
    file_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> RunsOut:
    require(principal, Action.USE_INGEST)
    with database.transaction(principal.tenant_context) as session:
        return RunsOut(data=[_run(r) for r in candidates.list_runs(session, principal, file_id)])


@router.get(
    "/files/{file_id}/candidates",
    summary="The questions found in a document (G-06)",
    description="Same visibility as the file, in page order.",
    responses={**_DENIED, **_NOT_FOUND},
)
def read_candidates(
    file_id: UUID,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    state: Annotated[str | None, Query(pattern="^(NEW|ACCEPTED|REJECTED|DUPLICATE)$")] = None,
    page_no: Annotated[int | None, Query(ge=1, le=10_000)] = None,
) -> CandidatesOut:
    require(principal, Action.USE_INGEST)
    with database.transaction(principal.tenant_context) as session:
        rows = candidates.list_candidates(session, principal, file_id, state=state, page_no=page_no)
        return CandidatesOut(data=[_candidate(r) for r in rows])


# --- One candidate ----------------------------------------------------------------------------


@router.get(
    "/candidates/{candidate_id}",
    summary="One candidate",
    responses={**_DENIED, **_NOT_FOUND},
)
def read_candidate(
    candidate_id: UUID,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> CandidateOut:
    with database.transaction(principal.tenant_context) as session:
        out = _candidate(candidates.get_candidate(session, principal, candidate_id))
    response.headers["ETag"] = etag(out.revision)
    return out


@router.put(
    "/candidates/{candidate_id}/content",
    summary="Fix a candidate's question",
    description=(
        "Replace the editable content (what the model read stays in `raw`). The question checks run"
        " again and their findings come back. Send the `revision` as the ETag."
    ),
    responses={**_DENIED, **_NOT_FOUND, **_DECIDED},
)
def edit_candidate(
    candidate_id: UUID,
    body: EditCandidate,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> CandidateOut:
    with database.transaction(principal.tenant_context) as session:
        row = candidates.update_content(
            session, principal, candidate_id, body.content, if_match=if_match
        )
        out = _candidate(row)
    response.headers["ETag"] = etag(out.revision)
    return out


@router.post(
    "/candidates/{candidate_id}/accept",
    summary="Create a question from a candidate",
    description=(
        "Makes a new **draft** question of the person's own, with the candidate's content, and"
        " remembers which page it came from. Needs the right to create questions. It does not"
        " submit or publish anything."
    ),
    responses={**_DENIED, **_NOT_FOUND, **_DECIDED},
)
def accept_candidate(
    candidate_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> CandidateOut:
    with database.transaction(principal.tenant_context) as session:
        return _candidate(
            candidates.accept(session, principal, candidate_id, request_id=_rid(request))
        )


@router.post(
    "/candidates/{candidate_id}/same-as",
    summary="This is a question the bank already has",
    description="Nothing new is made; the candidate points at the existing question you can open.",
    responses={**_DENIED, **_NOT_FOUND, **_DECIDED},
)
def same_as_candidate(
    candidate_id: UUID,
    body: SameAs,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> CandidateOut:
    with database.transaction(principal.tenant_context) as session:
        return _candidate(
            candidates.same_as(
                session, principal, candidate_id, body.question_id, request_id=_rid(request)
            )
        )


@router.post(
    "/candidates/{candidate_id}/reject",
    summary="Reject a candidate",
    responses={**_DENIED, **_NOT_FOUND, **_DECIDED},
)
def reject_candidate(
    candidate_id: UUID,
    body: RejectCandidate,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> CandidateOut:
    with database.transaction(principal.tenant_context) as session:
        return _candidate(
            candidates.reject(
                session, principal, candidate_id, body.reason, request_id=_rid(request)
            )
        )


@router.get(
    "/candidates/{candidate_id}/duplicates",
    summary="Questions the bank already has that read like this one (D-16)",
    description="Exact copies first, then near ones, among the questions the person can see.",
    responses={**_DENIED, **_NOT_FOUND},
)
def candidate_duplicates(
    candidate_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> DuplicatesOut:
    timeout: int = request.app.state.settings.search_timeout_ms
    with database.transaction(principal.tenant_context) as session:
        found = candidates.duplicates(session, principal, candidate_id, timeout_ms=timeout)
        return DuplicatesOut(
            data=[
                DuplicateOut(
                    question_id=d.master_id,
                    code=d.code,
                    exact=d.exact,
                    similarity_percent=d.similarity_percent,
                    preview=d.preview,
                )
                for d in found
            ]
        )


__all__ = ["State", "router"]
