# 9. Content Review and Publication Workflow

## Why this is separate from ingestion QC

Ingestion QC answers:

> Did we correctly extract the source material?

Content QC answers:

> Is this a correct, high-quality question that the organization is willing to publish?

## Lifecycle

```text
DRAFT
  -> IN_REVIEW
      -> REJECTED
      -> APPROVED
          -> PUBLISHED
              -> SUPERSEDED / ARCHIVED
```

## Creator responsibilities

- Correct content.
- Add/update metadata.
- Resolve ingestion problems.
- Submit for review.

## Reviewer responsibilities

- Physics/content correctness.
- Correct answer.
- Solution correctness.
- Metadata/taxonomy.
- Difficulty.
- Diagram/equation quality.
- Language quality.
- Duplicate/variant classification.

## Approver responsibilities

- Confirm final quality and organizational readiness.
- Approve publication.

## State transition rules

### DRAFT → IN_REVIEW
Requires mandatory fields and creator submission.

### IN_REVIEW → REJECTED
Reviewer provides structured rejection reason.

### IN_REVIEW → APPROVED
All critical checks pass.

### APPROVED → PUBLISHED
Authorized publisher/approver performs publication.

### PUBLISHED → EDIT
Never edit in place. Create a new version.

## Critical validation checklist

A question cannot be approved if any required item fails:

- Question type valid.
- Answer present and verified.
- Stem complete.
- Required options present.
- Required solution present according to organization policy.
- Required diagram assets exist.
- Taxonomy assigned.
- Difficulty assigned.
- Source attribution present where required.

## Physics validation

For important content classes, support explicit expert checks:
- Dimensional consistency.
- Sign conventions.
- Unit consistency.
- Boundary cases.
- Numerical recalculation.
- Option uniqueness.
- Diagram consistency.

## Reviewer disagreement

Do not silently overwrite another reviewer's decision.

Recommended mechanism:

```text
Question -> Review Task A -> PASS
        -> Review Task B -> FAIL
                    |
                    v
              Conflict state
                    |
                    v
             Expert resolution
```

## Publication lock

On publication:
- Freeze version content.
- Freeze direct metadata snapshot used by the version.
- Record publication actor and timestamp.
- Generate content hash.
- Prevent direct mutation.

A new version is required for changes.
