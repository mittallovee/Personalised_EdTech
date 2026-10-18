# Product Requirements — Question Bank

Review baseline: **18 October 2026**. Product policies below are confirmed; linked engineering designs remain proposals.

## Outcome

Faculty should turn varied source documents or manual entries into searchable, well-classified, reviewed coaching-owned questions without blocking other work. Preserve source evidence, correct answers, mathematical content and stable published history. Prepare stable concept identities for later personalized learning.

## People and ownership

Platform admin manages all coachings and supported capabilities. Each coaching has an Owner, multiple admins and invited/created faculty. Content belongs to the coaching, including after a faculty member leaves. Faculty sees the complete own-coaching bank; another coaching remains private. Platform authority is explicit and auditable.

Admin grants formal QC, approval, publication and cross-author editing independently. Faculty receives upload/manual/AI/view access by default. Creator may exercise formal actions only with matching grants; no universal second-person rule. Any QC-authorized faculty can use the shared pending queue. See [permissions](PERMISSIONS_MATRIX.md).

## Release-one journeys

| Journey | Required outcome |
| --- | --- |
| Coaching setup | Platform admin creates coaching/first Owner/name/logo; common app URL |
| Faculty access | Admin invite/create, canonical verified login linkage, single-coaching membership and concurrent device use |
| Manual entry | Save incomplete drafts; type-aware editor with visual/LaTeX/MathML equations and assets |
| Bulk intake | Mixed PDF/DOC/DOCX/images, accepted size limits, per-file errors, private retained originals |
| Extraction | Printed/scanned/handwritten questions/solutions, source anchors, formulas/figures, reusable layout patterns and visible uncertain regions |
| Separate sources | AI identifies paper/key/solution relationships; faculty corrects associations without losing evidence |
| Background work | Durable jobs, revisitable progress, further uploads/navigation, own-job cancellation and recoverable partial drafts |
| Review | Correction-return/resubmission, revision-bound human QC, approve and publish through separately authorized actions |
| Bank | Bounded search/filter, same-coaching duplicate suggestions, exact-duplicate source attachment, archive/restore |
| Knowledge graph | Primary/multiple secondary concepts, same-subject prerequisite navigation across classes; faculty opens linked questions |
| AI assistance | Enabled model choice, on-demand variants/translation/diagrams/solve/check, direct validated metadata and provisional taxonomy |
| Administration | Faculty cost/budgets, storage/original deletion, in-app taxonomy alerts, user/admin/Owner management |
| Independent seeding | Platform-admin one-time complete educational copy to another coaching, published status retained, new destination codes, no live sync |

## Content and publication

Nine formats are required: SCQ, multiple-correct, integer, single digit, numerical, matching, assertion–reason, multiple statement and passage-based groups. The [type specification](QUESTION_TYPES_SPECIFICATION.md) defines exact constraints; [schema examples](QUESTION_SCHEMA_EXAMPLES.md) supply proposed payloads.

A question has an internal UUID, an eight-character globally unique permanent alphanumeric code, and separate versions. Correction preserves its code. Variant/translation receives a new code and source-version relationship. Passage children have separate codes. Published snapshots preserve content, assets, taxonomy labels and passage versions.

Required at publication: type-valid content and answer, class, subject, exactly one chapter and topic, primary concept, difficulty 1–10, Bloom level; PYQ exam/year when marked PYQ; valid human QC/approval/publication authorization. Solution/subtopic/PYQ date/shift/paper code/video link remain optional. No separate numerical-answer unit field. See [publication rules](PUBLICATION_REQUIREMENTS.md).

## AI and classification

AI fills metadata directly in the question language. It uses stable catalogue IDs; absent concepts can be added/used immediately with pending-admin-review status. Same policy applies to AI prerequisite links; admin can later correct/revoke, and merge concepts. Only admin/authorized AI creates taxonomy entries. Faculty edits assignments through ordinary edit rights. Normal UI shows current metadata, while backend provenance/history remains.

English/Hindi/Gujarati/Bengali/Marathi/Telugu/Tamil initially, admin-extensible. One language at a time. Faculty requests translation after source review, not necessarily publication; translated master is independent.

Variants are faculty-requested, may use unreviewed sources, can mix count/type/difficulty targets and instructions, and preserve primary concept. Diagram generation/editing and solving/checking run on request. Checking flags and suggests; explicit per-question opt-in may apply a correction with visible old/new values/reason. Protected edits and published-version rules apply at write time.

Google, Anthropic, OpenAI and OpenRouter initially; add more later through supported adapters/catalogue entries. Each coaching uses its own keys, admin enabled models/default and faculty compatible selection. Automatic failure fallback is bounded, visible and same-coaching only. AI success never alone grants human QC, publication or an AI-verified badge.

Admin sees actual/estimated/unknown usage costs. Monthly per-faculty budgets: 80% warning, 100% new-work stop, first-day calendar-month reset with history retained. In-flight calls still require honest reconciliation.

## Source and pattern behavior

PDF/DOC/DOCX/images; 50 MB/document, 10 MB/image. Originals persist until admin deletion, faculty can view them, storage/delete is admin-only. Saved questions and required diagrams survive source deletion.

For unknown layouts, AI extracts and derives structured reusable patterns. Subsequent compatible layouts reuse saved versions automatically; multiple layout families/page sections and handwriting are included. Coverage/type validation, drift handling and AI fallback remain. Do not reuse a learning file's answers. Recognition and other AI costs remain; no token/accuracy/speed savings have been measured.

## Organization copy

Only platform admin initiates complete educational dataset/pattern copying. Independent destination identities/resources/codes, source provenance, original publication state and no ongoing synchronization. Copy excludes users/auth/session/grants/API keys and does not import source costs as destination spend. Destination can use/edit under its own roles. See [copy contract](CROSS_COACHING_DATA_SHARING.md).

## Current exclusions and later phases

No first-release test assembly, paper export, student attempts/analytics/recommendations, coaching subscription/payments, faculty courses/live/recorded delivery or AI teaching/personalized concept-video generation. These remain required later directions with their own milestone discovery.

No notification emails; only in-app notifications. No user-facing logged-in-device list/remote per-device logout. Question video solution is an optional external link, with no first-release video hosting.

## Environment, quality and completion

Development hosting is this PC; production hosting and hosted infrastructure budget are deferred. One initial coaching/few faculty and expected lakh-scale bank guide design, not a verified capacity promise.

Release completion requires all release-one flows and [planned acceptance scenarios](ACCEPTANCE_TEST_PLAN.md), tenant/role/version/asset integrity, representative extraction and provider evaluations, and documentation reflecting actual behavior. No such application checks have run. Later source samples do not block this documentation package.
