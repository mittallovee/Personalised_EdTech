# AI Answer Assistance — First-Release Requirement

Consolidation note (18 October 2026): current policy is retained below. [Technical proposals](TECHNICAL_DESIGN_PROPOSALS.md), [schema](DATABASE_SCHEMA.md) and [API](API_CONTRACTS_DRAFT.md) now provide concrete implementation recommendations; remaining empirical/engine choices are milestone work, not further required interview questions.


Status: faculty-requested solving/filling of missing answers and checking existing answers/solutions are confirmed first-release scope on 17 October 2026. Models, evaluation, limits and detailed interaction remain design work. No solving capability has been implemented or validated.

## Confirmed scope

- If an imported question has no available answer, faculty may request AI to solve it and fill the answer.
- This is on demand, not automatic solving of every uploaded question.
- Preserve that the filled answer came from an AI operation, not an original source answer key.
- The answer remains subject to normal human QC, type validation and authorized approval/publication.
- AI generation alone cannot set AI-verified status.

## Proposed operation contract

Input includes the exact candidate/question revision, complete relevant content/assets/passage, tenant/actor, supported selected/default model and prompt/schema version. Check source access and sufficient content. Do not invent unavailable figures, options or source-key evidence.

Validate returned answer structure against the question type: option identities/count, integer/single-digit limits, numerical precision/domain/range and matching rules. Preserve warnings/uncertainty or operation failure. An answer with extra numerical precision is flagged rather than automatically rounded.

Fill editable missing-answer work with provenance after successful validation. Do not overwrite an existing human answer silently or mutate a published version. Repeated operations and concurrent edits need revision-aware handling. Question identity does not change simply because a missing answer is filled; published corrections still create a new version.

## Quality and boundaries

Schema validity is not proof that the proposed answer is correct. Mathematical/subject consistency must be evaluated with representative questions and normal QC. If no reliable structured output is available, retain the candidate as unresolved rather than fabricating a usable key.

Solutions remain optional for publication. This answer-assistance decision does not require generating a full solution for every question or automatically translating/generating variants. Verification badges and independent checking criteria remain separate decisions.

## Acceptance direction

Demonstrate an explicit faculty request for a missing-key candidate, traceable answer output, correct type validation, no automatic upload-wide solving, safe failures, preserved source/provenance, tenant isolation and no automatic verification/publication. Tests have not been run.

## Existing answer and solution checking — confirmed

Faculty may explicitly request AI to check an existing answer and, when supplied, its solution for correctness in the first release. This complements missing-answer solving; it is not automatic checking of every upload. A solution is still optional for publication, so checking an answer must not require a solution to be invented first.

Design direction: check the exact question revision, answer, available solution, relevant options, passage and diagrams. Return reviewable findings with reasons and uncertainty or a clear inability/error outcome. Keep tenant/actor, input revision, provider/model/prompt and operation evidence. Do not silently replace an existing answer/solution, grant human QC authority, approve or publish. Findings attached to an old revision cannot silently be presented as checking changed content.

Use the coaching's enabled compatible models, credentials, background-job and spending policies. Requesting this AI operation uses the existing faculty AI-tool access; it does not confer formal QC/approve/publish permissions or permission to edit another faculty member's question. An AI check result is advisory evidence. Flagging, correction suggestions and explicit opt-in direct application are confirmed below. The precise verification-badge criteria remain open; successful execution or a model saying correct is not sufficient to assert an approved AI-verified badge.

Acceptance: cover an explicit request, answer-only input, supplied-solution input, disagreement/uncertainty, missing context and provider failure, revision changes during processing, tenant isolation, cost/provenance and unchanged protected content/status. These are planned scenarios, not executed capability tests.

## Flag, suggest and optionally apply corrections — confirmed

When an AI check identifies a suspected error, show the flag/findings and a suggested corrected answer or solution. Faculty may explicitly opt in to having the AI correction applied directly. Applied changes must still be shown, including the previous value, new value and reason; direct application is not a hidden overwrite. Without that opt-in, checking and suggestions leave existing content unchanged. Direct-correction opt-in is chosen separately for one question at a time. A single opt-in cannot apply corrections across a batch or carry over to other questions. This decision concerns correction application, not bulk upload or the scope of other AI tools.

Design direction: bind the opt-in, input revision and intended correction scope to the operation. Apply only a valid structured correction against the unchanged target revision and after checking the requesting user's current edit permission and tenant access. Check again when background results are applied; AI-tool access alone does not grant cross-author editing. Stale/concurrent changes, invalid or uncertain output, or lost authorization must leave existing content intact and show the conflict/failure or unresolved finding. Preserve numerical precision flagging and other question-type rules; opt-in does not waive them.

Retain original source keys/solutions, earlier content, model/prompt/requester provenance and application history. An applied correction keeps the question master/code: a published question receives an editable new version while the published snapshot remains unchanged. Changed content cannot silently inherit the old revision's QC/approval or verification evidence. Normal review, approval and publication permissions remain in force. A correction suggested by AI is not a guarantee of correctness, and an absent optional solution is not made mandatory by this feature.

Acceptance direction: compare no-opt-in and opted-in behavior, flag/suggestion and before/after visibility, validation, stale-result conflicts, tenant/edit authorization at application time, source preservation, same-master versioning for published content and unchanged approval/publication authority. No application checks have been executed.
