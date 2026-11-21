from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from qbank.modules.ai.names import Mode, Operation, Provider, Scope


class SetKey(BaseModel):
    """The key as the provider gave it. Write-only: no response ever carries it."""

    key: SecretStr = Field(
        description="The provider's API key, as copied from the provider. It is sealed on the"
        " server and never shown again; only its last four characters are.",
    )


class ProviderKeyOut(BaseModel):
    provider: Provider
    configured: bool
    last4: str | None = Field(
        description="The last four characters, so a person can tell which key is stored."
    )
    updated_at: datetime | None


class KeysOut(BaseModel):
    encryption_ready: bool = Field(
        description="False when the server has no master encryption key: keys cannot be stored"
        " until whoever runs the server sets `AI_KEYS_MASTER_KEY`."
    )
    data: list[ProviderKeyOut]


# --- The model list (H-03, H-17) -----------------------------------------------------------------

Price = Annotated[Decimal, Field(ge=0, le=100000, max_digits=12, decimal_places=6)]
Discount = Annotated[Decimal, Field(gt=0, le=1, max_digits=5, decimal_places=4)]


class OverlayOut(BaseModel):
    """What the admin entered; null where nothing was entered (the provider's value counts)."""

    supports_vision: bool | None
    supports_json: bool | None
    price_in: str | None
    price_out: str | None
    batch_supported: bool | None
    batch_discount: str | None


class ModelOut(BaseModel):
    id: UUID
    provider: Provider
    model_id: str
    display_name: str
    enabled: bool
    available: bool = Field(
        description="False when the provider's list no longer includes it; it cannot be enabled."
    )
    supports_vision: bool | None = Field(description="Effective: the overlay, else the provider's.")
    supports_json: bool | None = Field(description="Effective: the overlay, else the provider's.")
    context_tokens: int | None
    price_in_per_mtok: str | None = Field(
        description="US dollars per million input tokens, effective; null = unknown."
    )
    price_out_per_mtok: str | None = Field(
        description="US dollars per million output tokens, effective; null = unknown."
    )
    price_source: Literal["PROVIDER", "ADMIN", "UNKNOWN"]
    batch_supported: bool = Field(
        description="Whether Economy (batch) runs are offered: only when the admin says so."
    )
    batch_discount: str | None
    overlay: OverlayOut
    fetched_at: datetime
    revision: int


class ProviderStateOut(BaseModel):
    provider: Provider
    configured: bool = Field(description="Whether the coaching has a key stored for it.")
    last_refreshed_at: datetime | None
    last_error: str | None = Field(
        description="The kind of failure of the last refresh (`AUTH`, `RATE_LIMITED`, `TIMEOUT`,"
        " `UNAVAILABLE`, `NO_KEY`, `KEY_UNREADABLE` ...), or null when it worked."
    )


class ModelsOut(BaseModel):
    data: list[ModelOut]
    providers: list[ProviderStateOut]


class OverlayIn(BaseModel):
    """Only what is sent changes. A value of `null` removes the admin's entry for that fact, so the
    provider's value counts again."""

    model_config = ConfigDict(extra="forbid")

    supports_vision: bool | None = None
    supports_json: bool | None = None
    price_in: Price | None = None
    price_out: Price | None = None
    batch_supported: bool | None = None
    batch_discount: Discount | None = None


class UpdateModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = Field(
        default=None, description="Offer the model to faculty (true) or stop offering it (false)."
    )
    overlay: OverlayIn | None = None


class RefreshIn(BaseModel):
    provider: Provider


class RefreshOut(BaseModel):
    job_id: UUID


# --- Operation defaults, the rate and budgets (H-03, H-05, H-06) ----------------------------------

Rate = Annotated[Decimal, Field(gt=0, le=10000, max_digits=10, decimal_places=4)]
Rupees = Annotated[Decimal, Field(ge=0, le=1000000000, max_digits=12, decimal_places=2)]


class SettingsOut(BaseModel):
    usd_to_inr: str | None = Field(
        description="Rupees per US dollar, as the admin entered it. Null = not entered: budgets"
        " cannot be applied until it is."
    )
    default_budget_inr: str | None = Field(
        description="Monthly budget per person in rupees where they have none of their own."
        " Null = no limit."
    )
    revision: int


class SaveSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usd_to_inr: Rate | None = Field(description="Null clears it.")
    default_budget_inr: Rupees | None = Field(description="Null = no limit.")


class ModelRef(BaseModel):
    id: UUID
    provider: Provider
    model_id: str
    display_name: str
    enabled: bool
    available: bool


class OperationOut(BaseModel):
    operation: Operation
    default_model: ModelRef | None
    mode: Mode
    fallbacks: list[ModelRef]
    problem: Literal["MODEL_UNAVAILABLE", "MODEL_DISABLED"] | None = Field(
        description="Why a run would refuse the chosen model today; null when it can be used."
    )
    revision: int = Field(description="0 until first saved. Send it as the ETag.")


class OperationsOut(BaseModel):
    data: list[OperationOut]


class SaveOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_model_id: UUID | None = Field(
        description="The model offered first (an id from the model list), or null for none."
    )
    mode: Mode = Mode.NOW
    fallback_model_ids: list[UUID] = Field(
        default_factory=list,
        max_length=2,
        description="Tried in order if the first model fails in a way that may pass.",
    )


class BudgetOut(BaseModel):
    user_id: UUID
    display_name: str | None
    monthly_inr: str
    revision: int


class BudgetsOut(BaseModel):
    data: list[BudgetOut]


class SaveBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly_inr: Rupees = Field(description="0 means this person may not use AI.")


# --- Usage and cost (H-05, H-06) ----------------------------------------------------------------


class UsageOut(BaseModel):
    period: str = Field(description="The month, `YYYY-MM`, in India time.")
    spent_usd: str = Field(
        description="What providers billed (and what is reserved for runs in progress)."
    )
    spent_inr: str = Field(
        description="The same in rupees, at the rate in force when each cost was recorded."
    )
    limit_inr: str | None = Field(
        description="The person's monthly budget (their own, else the coaching's default);"
        " null = none."
    )
    remaining_inr: str | None = Field(
        description="What is left of the budget; null when there is no limit or no rate."
    )
    state: Literal["NO_LIMIT", "OK", "WARNING", "REACHED", "OFF"] = Field(
        description="`WARNING` from 80 % of the budget, `REACHED` at 100 % (new runs are refused),"
        " `OFF` when a budget is set but no dollar-to-rupee rate has been entered."
    )


class PersonUsageOut(UsageOut):
    user_id: UUID
    display_name: str | None


class UsageListOut(BaseModel):
    period: str
    data: list[PersonUsageOut]


class AdjustUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    amount_usd: Annotated[Decimal, Field(max_digits=12, decimal_places=6)] = Field(
        description="US dollars to add (positive) or take off (negative) this month's usage."
    )
    note: str = Field(min_length=1, max_length=300, description="Why, e.g. the invoice it follows.")


# --- The prompt library (H-13) --------------------------------------------------------------------

Temperature = Annotated[Decimal, Field(ge=0, le=1, max_digits=3, decimal_places=2)]


class VersionSummary(BaseModel):
    id: UUID
    version_no: int
    change_note: str
    author_id: UUID | None
    author_name: str | None
    created_at: datetime
    temperature: str | None
    content_hash: str


class VersionOut(VersionSummary):
    template_id: UUID
    instructions: str = Field(description="The editable part: plain text with `{{placeholders}}`.")
    operation: Operation
    scope: Scope
    is_active: bool


class TemplateOut(BaseModel):
    id: UUID
    scope: Scope
    operation: Operation
    name: str
    target_language: str | None
    owner_user_id: UUID | None
    revision: int = Field(description="Send as the ETag to activate, reset, adopt or dismiss.")
    active_version: VersionSummary | None = Field(
        description="The version in use (for a personal prompt, its latest). A coaching prompt with"
        " none follows the platform default."
    )
    latest_version: VersionSummary | None
    update_available: VersionSummary | None = Field(
        description="A newer platform default this coaching's prompt has not looked at yet."
    )


class TemplatesOut(BaseModel):
    data: list[TemplateOut]


class LockedPartsOut(BaseModel):
    operation: Operation
    safety_preamble: str
    required_placeholders: list[str]
    optional_placeholders: list[str]
    max_instruction_chars: int


class LockedOut(BaseModel):
    data: list[LockedPartsOut]


class VersionsOut(BaseModel):
    data: list[VersionSummary]


class SaveVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Scope = Field(
        description="Where the prompt lives: coaching, personal or (platform admin) platform."
    )
    operation: Operation
    template_id: UUID | None = Field(
        default=None, description="Add to this prompt; otherwise the prompt is found or started."
    )
    name: str | None = Field(
        default=None, max_length=100, description="Required to start a personal prompt."
    )
    target_language: str | None = Field(
        default=None,
        max_length=3,
        description="Translation only: a coaching prompt for one target language.",
    )
    instructions: str = Field(max_length=10000)
    temperature: Temperature | None = None
    change_note: str = Field(min_length=1, max_length=300)


class SavedVersion(BaseModel):
    template: TemplateOut
    version: VersionOut


class ActivateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: UUID


class ValidateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Operation
    instructions: str = Field(max_length=20000)


class ProblemOut(BaseModel):
    code: str
    message: str


class ValidateOut(BaseModel):
    ok: bool
    problems: list[ProblemOut]


class DiffLineOut(BaseModel):
    op: Literal["same", "removed", "added"]
    text: str


class DiffOut(BaseModel):
    changed: bool
    lines: list[DiffLineOut]
    temperature_from: str | None
    temperature_to: str | None


# --- The translation glossary (H-14) ------------------------------------------------------------


class GlossaryEntryOut(BaseModel):
    id: UUID
    language: str
    source_term: str
    target_term: str
    note: str | None
    revision: int = Field(description="Send as the ETag to change or remove the entry.")
    updated_at: datetime


class GlossaryOut(BaseModel):
    data: list[GlossaryEntryOut]


class AddGlossaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str = Field(max_length=3, description="The target language tag, e.g. `hi`.")
    source_term: str = Field(min_length=1, max_length=200)
    target_term: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=300)


class ChangeGlossaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_term: str = Field(min_length=1, max_length=200)
    target_term: str = Field(min_length=1, max_length=200)
    note: str | None = Field(default=None, max_length=300)
