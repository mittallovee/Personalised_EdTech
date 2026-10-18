# 4. Functional Requirements

## FR-001 Authentication

The system shall support:
- Email/password authentication.
- Google OAuth.
- Session management.
- Password reset.
- Optional organization domain restrictions.
- Account deactivation.

## FR-002 Organizations

The system shall support:
- Multiple organizations.
- Organization membership.
- Role assignment.
- Tenant-isolated content and configuration.
- Organization status: active/suspended/archived.

## FR-003 Manual question creation

A user with permission shall be able to create a question manually with:
- Question type.
- Language.
- Stem/content blocks.
- Options when applicable.
- Correct answer.
- Solution.
- Diagram/assets.
- Metadata.
- Source information.
- Difficulty.
- Exam/PYQ information.

## FR-004 Bulk ingestion

The system shall accept PDF, DOC, and DOCX files and create ingestion batches.

The ingestion subsystem shall preserve:
- Original file.
- File hash.
- Pages.
- Extraction artifacts.
- Source locations.
- Parsed question candidates.

## FR-005 Ingestion review

Reviewers shall compare source material and extracted content side-by-side and:
- Correct extraction.
- Correct answer.
- Correct question type.
- Correct metadata.
- Accept/reject diagrams and equations.
- Decide New Master / Existing Master / Variant / Duplicate.
- Submit/commit to Question Bank.

## FR-006 Versioning

Published versions shall be immutable.
Changes create a new version.

## FR-007 Master questions

Each conceptual question shall have a stable permanent ID independent of taxonomy/language/version.

Permanent IDs shall be non-semantic and randomly generated, approximately 7–8 alphanumeric characters.

## FR-008 Variants

Variants shall retain a relationship to a parent Master Question but have independently versioned content.

## FR-009 Multilingual

Support at least English and Hindi in the content model, with architecture allowing Bengali, Gujarati, and additional languages.

## FR-010 AI actions

AI actions shall include at minimum:
- Generate question.
- Modify question.
- Tag metadata.
- Translate.
- Generate solution.
- Analyze diagram.
- Generate diagram description/prompt.
- Detect duplicates.
- Verify question/answer.
- Generate explanation.

## FR-011 AI model selection

The platform shall maintain an approved model registry.

The user may select a model for an action only when:
- Model is active.
- Action is supported.
- User has selection permission.
- Organization policy permits it.

## FR-012 AI provenance

Every AI output that changes content shall record model, model version, gateway, prompt version, initiating user, input/source version, output, usage, cost where available, and validation outcome.

## FR-013 Search

Users shall search by:
- Full text.
- Fuzzy text.
- Metadata.
- Question IDs.
- Source.
- Exam/PYQ fields.
- Content availability.
- Status.

## FR-014 Duplicate detection

The platform shall identify exact, near-semantic, and potential-variant relationships.

AI suggestions must remain reviewable.

## FR-015 Test Builder

Test creators shall:
- Filter questions.
- See count available.
- Filter for text solution.
- Filter for video solution.
- Filter by question type, subject, chapter, topic, concept, difficulty, exam, year, etc.
- Control variant/master duplication.
- Order questions.
- Save draft tests.
- Create immutable test versions on publication.

## FR-016 Audit

All significant changes shall be auditable.

## FR-017 Bulk operations

Reviewers shall bulk-update eligible metadata, assignments, status, and duplicate decisions while respecting permission and workflow rules.

## Non-functional requirements

- Strong tenant isolation.
- Secure authentication.
- API idempotency for critical operations.
- Asynchronous long-running jobs.
- Horizontal scalability for workers.
- Full structured logs and trace IDs.
- Backups and restore testing.
- WCAG-aware UI practices.
- Reliable mathematical rendering.
