# AI Orchestration

Consolidated 18 October 2026. Confirmed product behavior below; adapter/accounting defaults are proposed under P-25–P-29. No provider integration or quality evaluation has run.

## Catalogue and providers

Initial support: **Google, Anthropic, OpenAI and OpenRouter**, extensible to more supported providers later. Each coaching supplies its own keys; admin selects enabled supported models/default and faculty selects compatible enabled choices. Model catalogue entries distinguish route provider, actual model identifier, operation/modality capabilities, status, last verification and optional price version.

Provider/model capabilities vary; never imply every enabled text model can edit images, read handwriting, render MathML or perform every operation. [Official references](TECHNICAL_REFERENCES.md) establish structured-output boundaries; exact model IDs/endpoints/prices/data handling require verification before enablement. Adding an adapter/catalogue entry is controlled engineering work, not arbitrary untrusted endpoint execution.

## Operation policy

| Operation | Trigger | Output/write boundary |
| --- | --- | --- |
| Extraction/layout discovery | Background intake for unknown/uncertain structure | Source-bound candidates and validated reusable pattern configuration |
| File pairing | Ingestion workflow | Direct paper/key/solution associations; faculty can correct |
| Metadata/tagging | Question intake/authorized update | Direct valid metadata in question language, stable catalogue IDs |
| Missing taxonomy/prerequisites | Authorized AI workflow | Immediately usable provisional same-coaching entities; admin app notification/review |
| Duplicate candidates | Every new intake | Same-coaching evidence/ranked candidates; human disposition |
| Variants | Faculty request, source review not required | New masters/codes, mixed count/type/difficulty/instructions; primary concept preserved; own QC |
| Translation | Faculty request after source QC | New master/code linked exact reviewed source; own QC/independent edits |
| Diagram generation/editing | Faculty request | New immutable asset, preserve original and normal question edit/version rules |
| Missing-answer solving | Faculty request | Fill editable missing key with AI provenance and type validation |
| Existing answer/solution check | Faculty request | Revision-bound flags/reason/suggestions; not automatic overwrite |
| Opt-in correction | Explicit consent for one question | Apply validated suggestion only with current edit authority/revision; show old/new/reason |

Solution remains optional. All AI tools are available to faculty by default; protected writes, human formal grants, source eligibility, budget and provider setup remain independent constraints.

## Proposed execution contract

A run identifies organization/requester, operation, exact input revision/assets/passage, requested target/consent, selected/default catalogue entry and prompt/output-schema versions. Before dispatch verify current membership/action, compatible enabled model, coaching credential, cancellation and budget reservation.

Provider adapters return structured content, finish/refusal/error state, usage and safe request/provider identifiers. Validate app schemas/reference ownership/ranges/coverage even with provider structured-output features. Refusal/incomplete/malformed/uncertain output is visible and never becomes a fabricated successful answer.

Store run and attempt provenance separately: requested/actual model/provider, route/upstream where available, prompt/schema/input/output versions, timestamps, safe failures, cost evidence and application revision. Do not log secrets or treat document instructions as trusted operations.

Fallback on eligible transient/model failure shows the error and automatically tries an enabled compatible alternative under the same coaching's keys/budget. Proposed bounded ordered attempts avoid retry loops. Do not change tenant, ignore authorization/budget stops or route around a safety refusal just to force output.

## Writes and verification

Recheck edit rights/input revision at completion; stale outputs remain inspectable evidence without overwriting current content. Direct metadata may populate editable work, not silently mutate a published snapshot. Checking consent applies to one question/revision and does not persist to the next question/batch.

Human QC/approve/publish remain separate. An AI-verified badge requires an approved evaluated evidence policy; none is established merely by successful generation/checking. Proposed release baseline displays provenance and advisory findings without asserting an earned verification badge.

## Evaluation

Separate layout recognition/structure, metadata, translation, scientific diagram accuracy, variant concept preservation, answering and checking quality. Include seven languages, math/figures and representative handwriting once samples arrive. Record actual/estimated/unavailable costs, fallback/retry overhead, correction effort and coverage. No accuracy/token-saving/capacity promise has been validated.

[Credentials](TENANT_AI_CREDENTIALS.md), [budgets](AI_USAGE_AND_COST.md), [patterns](ADAPTIVE_EXTRACTION_PATTERNS.md), [specific AI tool documents](README.md).
