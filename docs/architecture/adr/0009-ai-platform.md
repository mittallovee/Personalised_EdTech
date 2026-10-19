# ADR-0009: AI provider adapters, live model catalogue, prompt library
- Status: Proposed · Date: 2026-10-18
## Context
Four providers at start (Anthropic, OpenAI, Google, OpenRouter), coaching-owned keys, users choose models from what providers offer today, editable/versioned prompts (incl. personal and one-off), budgets, full provenance.
## Decision
- One internal interface `AIProvider` (`list_models`, `generate_structured`, capability flags, usage/cost extraction); one adapter per provider using official SDKs/HTTP APIs. No provider names in business code.
- **Live model catalogue**: a job calls each provider's model-list endpoint with the coaching's key (on demand + daily); results stored with fetch time; admin enables models. Capability/price come from provider metadata where available, else an admin-editable overlay; unknown price is shown as unknown.
- **Prompt library** (see `docs/product/03-ai-prompt-library.md`): immutable prompt versions at platform/coaching/personal scope; locked output JSON schema + safety preamble per operation; placeholder-only rendering.
- Every AI call goes through the orchestrator: permission → budget reservation → prompt resolution → model call → schema validation → domain validation → persist run/attempt/usage → apply (only if allowed).
- Keys encrypted at rest with a master key held outside the DB (env/secret manager); write-only in API.
- **Economy (batch) runs** (H-18, added 19 Oct 2026): the interface gains `submit_batch`,
  `batch_status`, `fetch_batch_results` and `cancel_batch`, offered only where the model's catalogue entry
  says batch is supported. The orchestrator splits into two steps on the ADR-0007 job queue:
  1. *Submit job*: permission → budget reservation → prompt resolution → `submit_batch`; the provider's
     batch ID and the run's input revision are stored on the run **before** the job completes, so a
     retried job finds the existing batch instead of submitting (and paying) twice (idempotency key =
     run ID, also sent to providers that accept one).
  2. *Collect job*: re-enqueued with a growing `run_after` (minutes, then hourly) until the provider
     reports a terminal state; then fetch results → schema/domain validation → persist usage → settle
     the reservation (actual charge on success; released on cancel/expiry/failure) → apply only if the
     question is still at the stored revision, else mark the result "out of date" → in-app notification.
  Provider batches survive our restarts because only IDs live on our side; a collect job is idempotent
  (re-reading a finished batch changes nothing). The detailed design is part of the M5 design note.
## Consequences
+ Adding a provider = one adapter; models update without code changes; every result is traceable.
− Capability metadata varies by provider; overlay needs occasional admin upkeep.
## Alternatives
LiteLLM as a dependency (useful, but adds a large surface; may be adopted inside an adapter later).
