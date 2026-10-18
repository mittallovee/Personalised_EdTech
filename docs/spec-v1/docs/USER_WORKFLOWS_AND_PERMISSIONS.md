# User Workflows

Consolidated 18 October 2026. Product authority is in [the matrix](PERMISSIONS_MATRIX.md); exact transition implementation is proposed in [lifecycle](QUESTION_LIFECYCLE_AND_QC.md).

## Coaching and user setup

Platform admin creates coaching, name/logo and first Owner. Owner appoints additional admins; any admin invites/creates ordinary faculty. Faculty activates a verified sign-in method and receives one coaching membership. Linked Google/password/OTP methods open the same account/grants/history. Concurrent devices are supported. No public coaching signup or device-management screen.

Owner may transfer to another active same-coaching admin; outgoing Owner remains admin. Removing an admin is an Owner decision between faculty demotion and app removal. Any admin may remove ordinary faculty. Data and historical attribution remain.

## Manual entry and intake

Faculty saves incomplete manual content in staging. Rich editor supports all answer formats and visual/LaTeX/MathML equations. File workflow accepts mixed bulk PDF/DOC/DOCX/images within limits and returns durable background jobs; further uploads/navigation continue.

Workers preserve source anchors, content/figures/handwriting/solutions, find paper/key/solution associations and reuse validated layout patterns. Faculty can correct associations/content within edit scope. Uncertain answer precision, ambiguous pairing, unsupported content and partial failure are visible; no silent answer fabrication.

Every new intake receives own-coaching duplicate checking. Human-confirmed exact intake adds the new source to the existing master without allocating a second code. Intentional variants/translations get separate codes. Manual/file/generated work converges on the same validation/QC pipeline.

## Review and publish

Creator/admin/cross-author editor prepares content. QC-authorized faculty uses the shared pending queue, passes QC or returns findings to creator. Corrected work resubmits. Approver and publisher need separate grants. One person can hold all grants; creation alone grants none.

Required answer/content/class/subject/one chapter/one topic/primary concept/difficulty/Bloom and conditional PYQ exam/year must be valid. Solution remains optional. Publication records an immutable snapshot. Later changes use a new version under the same code. Proposed revision mechanics prevent old approvals authorizing changed content.

## AI faculty work

Faculty selects coaching-enabled compatible models/default:
- Metadata fills directly in question language. Missing catalogue concepts/prerequisites may be immediately used provisionally; admin app review follows.
- Variants run on request, even from unreviewed content, with count/mixed type/difficulty/instructions and the original primary concept.
- Translation runs on request after source review; new independent question/code.
- Diagram generation/editing, solving missing keys and checking existing answers/solutions run on request.
- Checking flags and suggests; optional explicit one-question direct application shows old/new/reason and checks current edit/revision authority.

AI cannot grant human review, approval/publication or an unearned verified badge. Failures are visible; compatible fallback stays in the coaching's credentials/budget.

## Bank and administration

Faculty searches/filters complete own-coaching content and navigates the concept graph. Creator/admin can archive/restore in scope without deleting history. Original files remain faculty-viewable until admin deletion; required independent assets survive.

Admin manages taxonomy review, faculty costs/monthly budgets and storage. Budget warnings at 80%, stop new AI work at 100%, calendar-month reset/history retained. In-app-only taxonomy alerts go to all active admins including Owner.

## Independent coaching copy

Platform admin selects source/target and starts an audited one-time educational dataset copy. Destination receives independent question/pattern/taxonomy/asset identities and new global codes, source publication states and provenance, no copied users/keys/sessions/grants. Destination may edit under normal local workflow; source/destination changes do not sync.

No actual workflows are implemented or tested. See [acceptance plan](ACCEPTANCE_TEST_PLAN.md) for planned evidence.
