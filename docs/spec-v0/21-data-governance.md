# 21. Data Governance and Content Integrity

## Ownership

Question-bank content belongs to the organization/tenant according to the organization's contractual policy.

A faculty member is an actor, not the owner of a question record.

## Source attribution

For every imported question, preserve source where known:
- Source name.
- Exam.
- Year.
- Slot/paper/batch.
- Exam date.
- Source question number.
- Source file/page.

## Content provenance

Distinguish:

```text
HUMAN
IMPORTED
AI_GENERATED
AI_MODIFIED
AI_TRANSLATED
AI_VERIFIED
MIGRATED
```

Multiple provenance events may apply to the same final version.

## Version history

Never destroy a published historical version.

## Copyright/source policy

The platform should support configurable organizational policies for storing and using third-party source material. Legal review is required for the organization's intended source usage.

## Data quality rules

Examples:
- Correct answer required before publish.
- Question type and answer model must agree.
- Numerical questions must have normalized answer data.
- MCQ must support multiple answer keys.
- Passage questions must reference a valid passage.
- Diagram references must resolve to valid assets.

## Audit retention

Keep publication/review/audit records according to organizational/legal retention requirements.

## Export

Support tenant-authorized export of:
- Questions.
- Metadata.
- Sources.
- AI provenance.
- Tests.

Exports should include schema version and generation timestamp.
