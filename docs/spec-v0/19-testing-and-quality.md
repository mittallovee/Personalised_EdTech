# 19. Testing and Quality Strategy

## Test pyramid

```text
                E2E
              /      \
        Integration  Contract
          /              \
                Unit
```

## Unit tests

Cover:
- State transitions.
- Permission rules.
- Duplicate classification logic.
- Question-type validators.
- Answer normalization.
- Taxonomy constraints.
- Test selection rules.

## Integration tests

Cover:
- Database transactions.
- Tenant scoping.
- File ingestion persistence.
- AI job persistence.
- Publication locking.

## Contract tests

Validate AI gateway response schemas and external integrations.

## End-to-end tests

Critical journeys:

1. Login.
2. Create manual question.
3. Upload ingestion batch.
4. Process one document.
5. Review and create Master.
6. Submit/review/approve/publish.
7. Search published question.
8. Create test using filters.
9. Publish test version.

## Property/invariant tests

Important invariants:

- Published versions are immutable.
- Every question version belongs to exactly one variant.
- Every variant belongs to exactly one Master.
- Tenant-owned content cannot cross tenant boundaries.
- One published current version per variant/language according to configured policy.
- A reviewer/approver cannot bypass required states.

## AI evaluation

Maintain a curated evaluation set containing:
- Easy questions.
- Difficult questions.
- Equations.
- Diagram-heavy questions.
- Passage questions.
- Ambiguous OCR samples.
- Multilingual examples.

Evaluate AI functions independently:
- extraction.
- classification.
- tagging.
- answer verification.
- translation.
- duplicate detection.

## Performance testing

Benchmark:
- question table at 100k / 500k / 1M+ records.
- bulk ingestion batches.
- concurrent reviewers.
- test-builder filtering/counts.
- duplicate candidate retrieval.

## Security testing

Include:
- tenant escape tests.
- authorization bypass attempts.
- IDOR tests.
- malicious file uploads.
- prompt injection through imported content.
- XSS in question content.
- SSRF where external URLs are accepted.

## Definition of done

A feature is complete only when:
- acceptance criteria pass.
- unit/integration tests pass.
- permissions are tested.
- audit events exist where needed.
- migrations are reversible/safe.
- monitoring exists for critical paths.
- documentation is updated.
