# 24. Engineering and Coding Standards

## General

- TypeScript strict mode.
- Prefer small modules with explicit interfaces.
- No hidden global state for domain rules.
- Validate at API boundaries.
- Keep business rules server-side.

## Naming

Use consistent domain vocabulary:

```text
MasterQuestion
QuestionVariant
QuestionVersion
IngestionBatch
IngestionItem
AIJob
AIModelVersion
TestVersion
```

Do not use “question” ambiguously where Master/Variant/Version matters.

## Database

- Use migrations.
- Use foreign keys.
- Avoid unbounded JSONB when relational structure is needed for querying.
- Add indexes based on access patterns and measured query plans.
- Use transactions for state transitions and relationship changes.

## API

- Validate request body/query params.
- Return stable error codes.
- Use idempotency where retries can duplicate work.
- Paginate large collections.
- Never authorize based only on UI state.

## Frontend

- Strict typing.
- Reusable form components.
- Permission-aware UI.
- Server remains authority.
- Avoid giant pages/components; split by domain.

## AI integration

Never scatter model names throughout business code.

Use:

```text
AIAction -> ModelPolicy -> ModelVersion -> Gateway
```

## Transactions

Treat these as atomic domain operations where practical:
- create Master + initial Variant + Version.
- approve version.
- publish version.
- ingestion decision commit.
- publish test version.

## Git workflow

Recommended:
- trunk/main protected.
- short-lived feature branches.
- pull requests.
- required CI.
- conventional commit style optional but useful.

## Code review checklist

- Security/authorization.
- Tenant isolation.
- Data integrity.
- Migration safety.
- Test coverage.
- Observability.
- Error handling.
- Performance implications.
- Backward compatibility.

## Definition of done

No production feature is “done” until docs, migrations, tests, observability, and permission rules are updated.
