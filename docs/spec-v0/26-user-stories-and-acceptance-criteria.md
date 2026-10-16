# 26. User Stories and Acceptance Criteria

## EPIC A — Organization access

### US-A01: Sign in
As an organization member, I can sign in securely so that I can access content belonging to my organization.

Acceptance criteria:
- Inactive memberships cannot access protected application pages.
- Organization context is resolved server-side.
- Failed authentication does not reveal whether an account exists.
- Successful sign-in creates a secure session.

### US-A02: Role-based access
As an admin, I can assign roles to members.

Acceptance criteria:
- Permission changes take effect on subsequent authorization checks.
- Users cannot grant themselves permissions.
- Cross-organization role changes are impossible.

## EPIC B — Manual question bank

### US-B01: Create question
As a creator, I can create a structured question.

Acceptance criteria:
- Required fields are validated.
- Supported question types enforce the correct answer structure.
- The new question begins in DRAFT.
- A Master Question ID is created once the question is committed.

### US-B02: Edit draft
As a creator, I can edit a draft question.

Acceptance criteria:
- Changes are saved without losing unrelated fields.
- Audit events are recorded for material edits.
- Published versions cannot be modified in place.

## EPIC C — Ingestion

### US-C01: Upload source document
As a creator/admin, I can upload documents into a batch.

Acceptance criteria:
- Supported PDF/DOC/DOCX files are accepted.
- File hash is recorded.
- Original file remains available.
- Invalid/malicious files are rejected before processing.

### US-C02: Review extraction
As a reviewer, I can compare the extracted question to the source.

Acceptance criteria:
- Source page is displayed.
- Extracted stem/options/solution/assets are editable.
- Field-level confidence is visible.
- Low-confidence items are discoverable.

### US-C03: Resolve identity
As a reviewer, I can classify an ingestion item as New Master, Existing Master, Variant, or Duplicate.

Acceptance criteria:
- Existing candidates are displayed.
- Decision is stored with reviewer and timestamp.
- Correct Master/Variant relationships are created.

## EPIC D — Review and publication

### US-D01: Submit for review
Acceptance criteria:
- Required fields are present.
- State changes to IN_REVIEW.
- Creator receives confirmation.

### US-D02: Review question
Acceptance criteria:
- Reviewer can approve/reject each required check.
- Answer verification is explicit.
- Reviewer can leave comments/reasons.

### US-D03: Publish
Acceptance criteria:
- Only authorized users can publish.
- Published version becomes immutable.
- Publication event and content hash are recorded.

## EPIC E — AI

### US-E01: Choose AI model
Acceptance criteria:
- User sees only models allowed for the action.
- Default model is preselected.
- Actual selected model version is recorded in the AI job.

### US-E02: AI tagging
Acceptance criteria:
- AI returns schema-valid metadata.
- Confidence is recorded.
- AI output can be accepted, edited, or rejected.

## EPIC F — Test Builder

### US-F01: Filter question bank
Acceptance criteria:
- Counts reflect exactly the same eligibility constraints as selection.
- Filters can include solution/video availability.
- Tenant and status constraints cannot be bypassed.

### US-F02: Avoid duplicate Masters
Acceptance criteria:
- ONE_PER_MASTER prevents more than one question from the same Master family.
- Variant policy is visible before selection.

### US-F03: Publish test
Acceptance criteria:
- Published test version is immutable.
- Questions resolve to reproducible approved/published content.
- A publication snapshot/hash is retained.
