"""Routes for what an admin sets for the AI features (M5 design note §4, §7)."""

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from qbank.core.auth import CurrentPrincipal
from qbank.core.db import Database, get_database
from qbank.core.etag import IfMatchHeader, etag
from qbank.modules.ai import settings
from qbank.modules.ai.models import AiModel
from qbank.modules.ai.names import Mode, Operation, Provider
from qbank.modules.ai.schemas import (
    BudgetOut,
    BudgetsOut,
    ModelRef,
    OperationOut,
    OperationsOut,
    SaveBudget,
    SaveOperation,
    SaveSettings,
    SettingsOut,
)
from qbank.modules.identity.public import display_names

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

_DENIED: dict[int | str, dict[str, Any]] = {
    403: {"description": "Only the Owner and admins (`PERMISSION_DENIED`)"}
}
_STALE: dict[int | str, dict[str, Any]] = {
    412: {"description": "Changed since you read it (`REVISION_STALE`)"},
    428: {"description": "`If-Match` is missing (`IF_MATCH_REQUIRED`)"},
}


def _text_or_none(value: Decimal | None) -> str | None:
    return None if value is None else format(value.normalize(), "f")


def _settings_out(view: settings.SettingsView) -> SettingsOut:
    return SettingsOut(
        usd_to_inr=_text_or_none(view.usd_to_inr),
        default_budget_inr=_text_or_none(view.default_budget_inr),
        revision=view.revision,
    )


def _ref(model: AiModel) -> ModelRef:
    return ModelRef(
        id=model.id,
        provider=Provider(model.provider),
        model_id=model.model_id,
        display_name=model.display_name,
        enabled=model.enabled,
        available=model.available,
    )


def _operation_out(view: settings.OperationView) -> OperationOut:
    return OperationOut(
        operation=view.operation,
        default_model=_ref(view.default_model) if view.default_model is not None else None,
        mode=view.mode,
        fallbacks=[_ref(model) for model in view.fallbacks],
        problem=view.problem,
        revision=view.revision,
    )


@router.get(
    "/settings",
    summary="The dollar-to-rupee rate and the default monthly budget (H-05)",
    description="Owner and admins. `revision` is also sent as the ETag. A coaching that has never"
    " saved has revision 0 and no rate or budget.",
    responses=_DENIED,
)
def get_settings(
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> SettingsOut:
    with database.transaction(principal.tenant_context) as session:
        result = _settings_out(settings.get_settings(session, principal))
    response.headers["ETag"] = etag(result.revision)
    return result


@router.put(
    "/settings",
    summary="Set the rate and the default monthly budget (H-05)",
    description="Owner and admins. Replaces both values (`null` = not set). Providers bill in US"
    " dollars and budgets are in rupees, so a budget cannot be applied until a rate is entered."
    ' Send the ETag you last read in `If-Match` (`"rev-0"` before the first save). Written to the'
    " audit log.",
    responses={**_DENIED, **_STALE},
)
def put_settings(
    body: SaveSettings,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> SettingsOut:
    with database.transaction(principal.tenant_context) as session:
        view = settings.save_settings(
            session,
            principal,
            usd_to_inr=body.usd_to_inr,
            default_budget_inr=body.default_budget_inr,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _settings_out(view)
    response.headers["ETag"] = etag(result.revision)
    return result


@router.get(
    "/operations",
    summary="The model and mode offered first for each operation (H-03)",
    description="Owner and admins. Always the four operations (`TAG`, `TRANSLATE`, `SOLVE`,"
    " `VERIFY`). `problem` says when the chosen model cannot be used today (it was disabled or the"
    " provider stopped listing it).",
    responses=_DENIED,
)
def get_operations(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> OperationsOut:
    with database.transaction(principal.tenant_context) as session:
        views = settings.list_operations(session, principal)
        return OperationsOut(data=[_operation_out(view) for view in views])


@router.put(
    "/operations/{operation}",
    summary="Choose the model, mode and fallbacks for an operation (H-03, H-04)",
    description="Owner and admins. Replaces the setting of one operation. The first model and each"
    " fallback must be enabled, listed by the provider and able to return JSON; Economy only for a"
    " model marked as offering batch runs. At most two fallbacks; a model appears once. Send the"
    ' operation\'s `revision` as the ETag (`"rev-0"` before the first save). Written to the audit'
    " log.",
    responses={
        **_DENIED,
        **_STALE,
        409: {
            "description": "A model is not enabled (`AI_MODEL_NOT_ENABLED`), no longer listed"
            " (`AI_MODEL_UNAVAILABLE`), cannot return JSON (`AI_MODEL_NO_JSON`), or is not set up"
            " for Economy (`AI_ECONOMY_UNAVAILABLE`)"
        },
        422: {"description": "A model is unknown or repeated, or too many fallbacks"},
    },
)
def put_operation(
    operation: Operation,
    body: SaveOperation,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> OperationOut:
    with database.transaction(principal.tenant_context) as session:
        view = settings.save_operation(
            session,
            principal,
            operation,
            default_model_id=body.default_model_id,
            mode=Mode(body.mode),
            fallback_model_ids=body.fallback_model_ids,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        result = _operation_out(view)
    response.headers["ETag"] = etag(result.revision)
    return result


@router.get(
    "/budgets",
    summary="Members who have a monthly budget of their own (H-05)",
    description="Owner and admins. Everyone else has the default from the settings.",
    responses=_DENIED,
)
def get_budgets(
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
) -> BudgetsOut:
    with database.transaction(principal.tenant_context) as session:
        views = settings.list_budgets(session, principal)
        names = display_names(session, [view.user_id for view in views])
        return BudgetsOut(
            data=[
                BudgetOut(
                    user_id=view.user_id,
                    display_name=names.get(view.user_id),
                    monthly_inr=_text_or_none(view.monthly_inr) or "0",
                    revision=view.revision,
                )
                for view in views
            ]
        )


@router.put(
    "/budgets/{user_id}",
    summary="Give a member a monthly budget of their own (H-05)",
    description="Owner and admins. In rupees; `0` means the person may not use AI. Send the"
    ' member\'s budget `revision` as the ETag (`"rev-0"` when they have none yet). Written to'
    " the audit log.",
    responses={
        **_DENIED,
        **_STALE,
        404: {"description": "No such member in this coaching (`NOT_FOUND`)"},
    },
)
def put_budget(
    user_id: UUID,
    body: SaveBudget,
    request: Request,
    response: Response,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> BudgetOut:
    with database.transaction(principal.tenant_context) as session:
        view = settings.set_budget(
            session,
            principal,
            user_id,
            monthly_inr=body.monthly_inr,
            if_match=if_match,
            request_id=request.state.request_id,
        )
        names = display_names(session, [user_id])
        result = BudgetOut(
            user_id=user_id,
            display_name=names.get(user_id),
            monthly_inr=_text_or_none(view.monthly_inr) or "0",
            revision=view.revision,
        )
    response.headers["ETag"] = etag(result.revision)
    return result


@router.delete(
    "/budgets/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Take a member's own budget away (H-05)",
    description="Owner and admins. The coaching's default applies to the member again. Send the"
    " budget's `revision` as the ETag. Written to the audit log.",
    responses={
        **_DENIED,
        **_STALE,
        404: {"description": "This member has no budget of their own (`NOT_FOUND`)"},
    },
)
def delete_budget(
    user_id: UUID,
    request: Request,
    principal: CurrentPrincipal,
    database: Annotated[Database, Depends(get_database)],
    if_match: Annotated[str | None, IfMatchHeader] = None,
) -> Response:
    with database.transaction(principal.tenant_context) as session:
        settings.clear_budget(
            session,
            principal,
            user_id,
            if_match=if_match,
            request_id=request.state.request_id,
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
