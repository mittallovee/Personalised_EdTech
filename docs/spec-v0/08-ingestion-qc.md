# 8. Ingestion QC Workspace

## UI objective

Process hundreds of imported questions with minimal context switching.

## Three-panel layout

```text
Source PDF | Extracted Question | QC + Metadata
```

### Source panel

- Page navigation.
- Zoom.
- Search.
- Original question number.
- Source file.

### Extracted content panel

- Stem.
- Options.
- Equations.
- Images.
- Solution.

### QC panel

- AI confidence.
- Metadata.
- Answer verification.
- Duplicate candidates.
- Master/Variant decision.

## Review checks

### Extraction
- No missing text.
- Correct ordering.
- Options complete.
- Special symbols/equations preserved.
- Diagram attached.

### Answer
- Answer key extracted.
- Solution-derived answer.
- AI-checked answer where available.
- Human verification.

### Metadata
- Question type.
- Subject/chapter/topic/concept.
- Difficulty 1–10.
- Bloom level.
- Exam/PYQ fields.
- Source fields.

### Classification

Reviewer chooses:
- New Master.
- Existing Master.
- Variant.
- Duplicate.

## Fast review mode

For high-confidence items:
- Approve extraction.
- Verify answer.
- Confirm metadata.
- Next.

## Detailed review mode

Triggered by:
- Low answer confidence.
- Extraction anomaly.
- Diagram issue.
- Duplicate score above threshold.
- AI validation conflict.

## Bulk review

Support:
- Bulk metadata updates.
- Bulk reviewer assignment.
- Bulk approve of eligible fields/items.
- Bulk duplicate marking only with explicit confirmation.

## Keyboard actions

Suggested defaults:

```text
Alt+N      Next
Alt+P      Previous
Ctrl+Enter Save / accept current review
D          Duplicate
V          Variant
M          Existing Master
N          New Master
R          Needs review
```

## Rejection reasons

Use structured reasons:
- Extraction poor.
- Wrong answer.
- Missing information.
- Duplicate.
- Bad source.
- Invalid question.
- Diagram issue.
- AI issue.
- Other.

Optional free-text note is retained.
