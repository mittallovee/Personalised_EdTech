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
  1. *Submit job*: permission → budget reservation → prompt resolution → mark the run `SUBMITTING`
     (committed) → `submit_batch`, tagging the batch with the run ID → store the provider's batch ID.
  2. *Collect job*: re-enqueued with a growing `run_after` (minutes, then hourly) until the provider
     reports a terminal state; then fetch results → schema/domain validation → persist usage → settle the
     budget → re-check authorization → apply only if the question is still at the stored revision →
     in-app notification.

  Guarantees the M5 design must keep (it details them; tests prove each):
  - **At-most-once submission (N-05).** `submit_batch` is called only by the job that moves the run
    from `QUEUED` to `SUBMITTING` (one conditional database update, so only one worker can win), and
    never again for that run: no automatic retry, overlapping worker or cancellation re-submits it. A run
    left `SUBMITTING` without a batch ID (crash, lost lease, unknown outcome) is resolved only by
    **reconciliation**: looking up the provider's batches for the run-ID tag until it is found (then
    adopted, and cancelled if the user cancelled meanwhile) or until the provider's visibility window has
    passed (then marked "submission unknown", reservation settled from the provider's usage records, and
    the user may start a new run). Economy is offered only for models whose provider supports such a lookup.
  - **Exact budget settlement.** Every terminal state, including cancellation and "submission unknown",
    replaces the reservation with the actual charge (zero, partial or full) and releases only the unused
    remainder; nothing stays reserved. Economy needs a known price for the model (H-17) to reserve against.
  - **Authorization at apply time (B-10).** Just before applying, the submitter's current membership and
    the operation's grant are checked again; if they no longer hold, or the question moved past the
    stored revision, the result is kept unapplied ("needs review" / "out of date") and never changes the
    question.
  - **Restart-safe and idempotent.** Only IDs and states live on our side; re-running a collect job on a
    finished batch changes nothing.
## Consequences
+ Adding a provider = one adapter; models update without code changes; every result is traceable.
− Capability metadata varies by provider; overlay needs occasional admin upkeep.
## Alternatives
LiteLLM as a dependency (useful, but adds a large surface; may be adopted inside an adapter later).
