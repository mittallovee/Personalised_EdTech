# 14. API Specification

## API principles

- REST/JSON initially.
- Version API under `/api/v1`.
- Authentication via session/JWT as selected by implementation.
- Tenant resolved server-side.
- Pagination on all collection endpoints.
- Idempotency for file upload finalization, publish actions, and other retry-prone mutations.
- Consistent error envelope.

## Error envelope

```json
{
  "error": {
    "code": "QUESTION_NOT_EDITABLE",
    "message": "Published question versions are immutable.",
    "requestId": "req_...",
    "details": {}
  }
}
```

## Authentication

```text
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/password/forgot
GET  /api/v1/auth/me
```

## Organizations

```text
GET  /api/v1/organizations
GET  /api/v1/organizations/:id
GET  /api/v1/organizations/:id/members
POST /api/v1/organizations/:id/members
PATCH /api/v1/organizations/:id/members/:memberId
```

## Taxonomy

```text
GET /api/v1/taxonomy/subjects
GET /api/v1/taxonomy/chapters
GET /api/v1/taxonomy/topics
GET /api/v1/taxonomy/concepts
```

## Questions

```text
POST /api/v1/questions
GET  /api/v1/questions
GET  /api/v1/questions/:masterId
POST /api/v1/questions/:masterId/variants
POST /api/v1/questions/:masterId/versions
PATCH /api/v1/question-versions/:versionId
POST /api/v1/question-versions/:versionId/submit-review
POST /api/v1/question-versions/:versionId/approve
POST /api/v1/question-versions/:versionId/publish
POST /api/v1/question-versions/:versionId/archive
```

Published version mutation should return a conflict/error and direct caller to version creation.

## Ingestion

```text
POST /api/v1/ingestion/batches
GET  /api/v1/ingestion/batches
GET  /api/v1/ingestion/batches/:id
POST /api/v1/ingestion/batches/:id/files
POST /api/v1/ingestion/batches/:id/process
GET  /api/v1/ingestion/items
GET  /api/v1/ingestion/items/:id
POST /api/v1/ingestion/items/:id/decision
POST /api/v1/ingestion/batches/:id/reprocess
```

## AI

```text
GET  /api/v1/ai/actions
GET  /api/v1/ai/actions/:action/models
POST /api/v1/ai/jobs
GET  /api/v1/ai/jobs/:id
POST /api/v1/ai/jobs/:id/cancel
```

## Search

```text
GET /api/v1/search/questions?q=...
GET /api/v1/questions/duplicates/candidates?questionVersionId=...
```

## Tests

```text
POST /api/v1/tests
GET  /api/v1/tests
GET  /api/v1/tests/:id
POST /api/v1/tests/:id/versions
PATCH /api/v1/test-versions/:id
POST /api/v1/test-versions/:id/questions
DELETE /api/v1/test-versions/:id/questions/:id
POST /api/v1/test-versions/:id/publish
```

## Pagination

Recommended cursor pagination for high-volume lists:

```text
GET /api/v1/questions?limit=50&cursor=...
```

Return:

```json
{
  "data": [],
  "page": {
    "nextCursor": "...",
    "hasMore": true
  }
}
```

## Idempotency

Support `Idempotency-Key` for operations likely to be retried by clients/workers.

## Authorization

Every endpoint must enforce resource-level tenant and role permissions server-side.
