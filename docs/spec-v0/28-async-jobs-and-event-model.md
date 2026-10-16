# 28. Async Jobs and Event Model

## Why asynchronous processing

Document extraction, image processing, AI calls, embeddings, and exports may take seconds or minutes. They must not block normal web requests.

## Core job types

```text
DOCUMENT_SCAN
DOCUMENT_EXTRACT
QUESTION_SEGMENT
QUESTION_STRUCTURIZE
ASSET_PROCESS
AI_ACTION
EMBED_QUESTION
DUPLICATE_SCAN
EXPORT_DATA
REPROCESS_BATCH
```

## Job envelope

```json
{
  "jobId": "...",
  "type": "AI_ACTION",
  "organizationId": "...",
  "entityId": "...",
  "attempt": 1,
  "createdAt": "..."
}
```

## Idempotency

A worker must safely process the same job more than once without producing duplicate Master/Variant records or duplicate side effects.

Use unique business keys where appropriate.

## Retry classification

Retry:
- temporary database outage.
- network timeout.
- transient provider 5xx.
- rate limit after backoff.

Do not blindly retry:
- invalid file.
- schema-invalid deterministic input.
- authorization failure.
- unsupported document.
- permanent provider rejection.

## Events

Recommended domain events:

```text
QuestionCreated
QuestionVersionCreated
QuestionSubmittedForReview
QuestionReviewed
QuestionApproved
QuestionPublished
QuestionArchived
IngestionBatchCreated
IngestionItemResolved
AIJobCompleted
TestPublished
```

Events are for decoupling and audit/analytics; they do not replace transactional state.

## Outbox pattern

For important events:

```text
DB transaction
  -> domain change
  -> outbox row
       |
       v
Publisher
       |
       v
Queue/event consumer
```

This prevents “database changed but event disappeared” failures.
