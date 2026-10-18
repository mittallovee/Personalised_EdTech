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
## Consequences
+ Adding a provider = one adapter; models update without code changes; every result is traceable.
− Capability metadata varies by provider; overlay needs occasional admin upkeep.
## Alternatives
LiteLLM as a dependency (useful, but adds a large surface; may be adopted inside an adapter later).
