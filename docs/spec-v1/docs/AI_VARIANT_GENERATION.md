# AI Variant Generation — First-Release Requirement

Consolidation note (18 October 2026): confirmed policy is retained below; concrete engineering defaults are in [technical proposals](TECHNICAL_DESIGN_PROPOSALS.md). Any remaining engine/library/quality choices are implementation evidence work, not additional required user questions.

Status: first-release feature, distinct variant identity and faculty-requested generation confirmed on 17 October 2026. Source review completion is not a prerequisite; faculty chooses variant count, target question type and target difficulty. Mixed target types/difficulties within one request are confirmed. Limits/defaults and provider choices remain under review. No model operation has been implemented or benchmarked.

## Confirmed scope

- First release includes AI generation of new practice variants by changing values/conditions and, if requested, question type and difficulty.
- Faculty can select how many variants to generate.
- Faculty can change the target question type and specify target difficulty on the agreed 1–10 scale. Record these requested targets in the generation plan/provenance.
- Keep the original question's primary concept unchanged in generated variants, including when type/difficulty changes. Use the stable concept identity rather than relying on matching label text.
- A single request can mix target types and difficulties, e.g. two SCQ variants at difficulty 4 and one numerical at difficulty 7. Preserve a count/type/difficulty plan for each requested group/item.
- Faculty may add optional free-text instructions, e.g. change only numerical values or reduce calculation. Record them with the generation plan/provenance; do not let them silently override required primary-concept preservation or format/permission rules.
- Generate only when faculty requests variants; do not automatically generate variants for every new/uploaded question.
- Original question need not have completed review. Draft/unreviewed sources can be used; resulting variants still follow their own normal QC and publication rules.
- A resulting variant is a distinct question master with a new globally unique eight-character alphanumeric code and its own versions.
- Preserve an explicit variant-of relationship to the original and trace the source question version.
- Organization ownership, tenant isolation and the controlled supported-model catalogue apply.
- AI output does not automatically become published or AI-verified. Applicable human QC, required fields and admin-defined approval/publication permissions still apply.
- Fixing an existing question is a correction version under its existing code; creating a new practice variant is a new identity.

## Generation contract — proposed detail

Input identifies the authorized organization/actor, exact source question version, permitted model/default, operation and prompt/schema versions, plus reviewed generation constraints. Faculty request is the confirmed trigger. Source review completion is not required. Faculty controls requested count, target question type and target difficulty (1–10). Validate source content/access and the requested targets without imposing a source-review gate. A batch may mix target types/difficulties. Exact count limits/defaults remain open.

Output should contain source/version provenance, structured candidate content, proposed answer, permitted metadata, warnings and model/prompt evidence. Validate the result against the selected question format and the agreed numeric, option, matching, passage and statement rules. A schema-valid answer is not proof of mathematical/subject correctness.

Re-evaluate answer, units, equations, option correctness, diagrams and secondary concepts when values or conditions change. Validate that generated content still tests the original primary concept; primary concept must remain unchanged. Flag semantic drift rather than relabeling unrelated content as compliant. Do not blindly copy a source answer or approved status. Solutions remain optional under publication policy; any generated solution must be checked for consistency when supplied.

Represent output as reviewable candidate/draft work and materialize the new master/code through the controlled question-bank workflow. Preserve the source; never overwrite its content. Idempotent retries must not create duplicate variant masters. Failures should retain safe error/provenance without inventing a usable result.

## Controls and evaluation still to define

Concrete request/write/concurrency/budget defaults are proposed in TECHNICAL_DESIGN_PROPOSALS.md and API_CONTRACTS_DRAFT.md (initial maximum 10 outputs, configurable; mixed targets and one-request instructions). Exact model capability and academic-quality evaluation remain unverified. Do not claim that enabling a catalogue entry proves generation quality for every question type/language.

## Acceptance direction

An authorized operation creates traceable draft variants, preserves the original, applies type validation, uses new codes and follows existing QC. Test cross-tenant denial, model/output failure, replay idempotency, invalid answers and source-relationship integrity. Publication remains a separately authorized action. These are planned tests, not executed evidence.

## Target type and difficulty — confirmed controls

Apply the selected target format, not blindly the source format. Regenerate/validate answer structure and required options/statement/matching/passage content as appropriate. Requested difficulty must be recorded separately from evaluated AI/human metadata so a target does not become an unsupported claim that output meets it. Preserve the source primary concept and reassess secondary concepts, units, mathematical consistency and diagrams after conversion. Generated content still enters normal QC. Supported target types refer to the first-release catalogue; mixed target batches are supported, while practical limits and model capability evaluation remain design work.

## First-release AI diagram creation/editing — confirmed

User-confirmed: first release includes AI generation of question diagrams and modification of existing diagrams when needed. Keep reviewable asset output, provenance, same-tenant attachment, preserved originals and version-safe references. Human QC checks diagram/question/answer consistency; no automatic verification or publication. Invocation controls, supported representation/providers/models and evaluation remain open. See [AI diagram assistance](AI_DIAGRAM_ASSISTANCE.md).

## Default faculty access — confirmed

All active faculty may request variants without a separate per-user admin enable flag. Normal tenant scope, on-demand trigger, source/content checks and configured resource limits apply. Editing another creator's existing question and approving/publishing still require their separate grants.
