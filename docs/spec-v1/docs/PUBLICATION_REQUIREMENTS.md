# Publication Requirements — Consolidated Review Decisions

Consolidation note (18 October 2026): confirmed policy is retained below; concrete engineering defaults are in [technical proposals](TECHNICAL_DESIGN_PROPOSALS.md). Any remaining engine/library/quality choices are implementation evidence work, not additional required user questions.

Status: user-confirmed field requirements collected during review on 17 October 2026. This is a product specification, not implemented validation. Exact review states and revision binding are now proposed in QUESTION_LIFECYCLE_AND_QC.md; they are engineering recommendations for review.

## Required before publication

| Field/check | Confirmed rule |
| --- | --- |
| Correct answer | Required and valid for the question format; numerical exact/range and option/mapping rules are specified in the question-type document |
| Class | Required |
| Subject | Required |
| Chapter | Exactly one required |
| Topic | Exactly one required |
| Primary concept | Required; an otherwise valid AI-added/admin-review-pending concept is immediately usable |
| Difficulty | Required on the agreed 1–10 scale |
| Bloom level | Required; valid catalogue identity with localized label |
| Exam name, if marked PYQ | Required for PYQ, not universally required for non-PYQ |
| Exam year, if marked PYQ | Required for PYQ, not universally required for non-PYQ |
| Authorization and workflow | Admin-defined publication permission, applicable valid review/approval state, tenant-safe references and audit |
| Version preservation | Publication locks the version; later corrections create another version without rewriting historical content |

Question content must be structurally valid and renderable for its type, including needed assets and passage context. A populated metadata checklist alone does not establish answer correctness or bypass human QC. Proposed content payloads and review-state contracts are in QUESTION_SCHEMA_EXAMPLES.md and QUESTION_LIFECYCLE_AND_QC.md.

## Confirmed optional fields

- Subtopic: optional; validate hierarchy if supplied.
- Solution/explanation: optional; a valid question may publish with a correct answer and no solution when other requirements are met.
- PYQ date: optional.
- PYQ shift/slot: optional.
- PYQ paper code: optional.
- Video solution: optional external link; video-file upload/hosting is not first-release scope.

Do not fabricate optional values or block publication merely because these fields are absent. Other optional metadata from the handover, such as video-solution information, remains part of the broader model; this document does not turn unreviewed fields into new mandatory checks.

## Draft versus published work

Incomplete drafts are saveable. Publication checks enforce required values, catalogue/tenant integrity, format rules and workflow permissions. AI directly fills metadata with provenance; each field does not require separate acceptance. Authorized users can correct values before publication. Source content and extraction warnings remain available for review.

Changing a published question, a taxonomy label, an asset or shared passage must not silently alter historical rendering. Proposed D-05/D-08 implementation uses immutable saved revisions and invalidates current QC/approval eligibility whenever content changes; old decisions remain bound to their prior revision.

## Related specifications and evidence

See [question formats](QUESTION_TYPES_SPECIFICATION.md), [taxonomy/AI updates](TAXONOMY_AND_KNOWLEDGE_GRAPH.md), [QC lifecycle](QUESTION_LIFECYCLE_AND_QC.md), [permissions](USER_WORKFLOWS_AND_PERMISSIONS.md), and [decisions](PRODUCT_DECISION_REGISTER.md). R-16/R-17/R-19 and AT-12/AT-13 cover the corresponding planned checks. No application tests have been executed.

## Numerical answer cardinality — confirmed

A numerical question supports one exact answer value or one inclusive accepted range, not multiple separate ranges. There is no separate numerical-answer unit field or unit-field publication requirement; preserve units in original evidence, question/equation/solution content without silently converting numeric values. Keep the 0.00–999.00 domain, two-decimal precision, ordered inclusive endpoints and existing precision-flag policy. Imported/AI multi-range evidence must remain visible for authorized correction; do not silently select one interval or bridge the gap by widening it. Incomplete/flagged drafts remain recoverable, but an invalid multi-range key cannot pass type validation for publication. Proposed precise storage/API representation is documented in the schema examples and database design. See [question formats](QUESTION_TYPES_SPECIFICATION.md).

## Published status in independent coaching copies - confirmed

When platform admin copies an existing coaching dataset, source-published question snapshots remain published in the destination without mandatory re-review merely for copying. Preserve source QC/publication provenance, the platform copy actor and exact version/dependency mapping; do not invent destination reviewer identities. New destination question masters still receive new globally unique codes. Validate complete snapshot/reference integrity; do not promote source drafts/unreviewed content. Later destination edits create a new editable version under the destination code and follow normal QC/approval/publication; copied published snapshots stay immutable. See [dataset sharing](CROSS_COACHING_DATA_SHARING.md).
