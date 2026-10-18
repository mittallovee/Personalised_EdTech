# 29. Environment and Configuration Reference

## Rule

Configuration belongs outside source code and secrets never belong in Git.

## Application

```text
NODE_ENV
APP_ENV
APP_BASE_URL
LOG_LEVEL
SESSION_SECRET
```

## Database

```text
DATABASE_URL
DIRECT_DATABASE_URL (optional for migrations)
```

## Object storage

```text
STORAGE_PROVIDER
STORAGE_BUCKET
STORAGE_REGION
STORAGE_ENDPOINT
STORAGE_ACCESS_KEY
STORAGE_SECRET_KEY
```

## Authentication

```text
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
AUTH_REDIRECT_URL
ALLOWED_EMAIL_DOMAINS
```

`ALLOWED_EMAIL_DOMAINS` must be policy/configuration, not hard-coded business logic.

## AI gateway

```text
AI_GATEWAY_BASE_URL
AI_GATEWAY_API_KEY
AI_DEFAULT_TIMEOUT_MS
AI_MAX_RETRIES
```

Provider keys should live in the gateway/secret store where possible rather than the application.

## Queue

```text
QUEUE_URL
WORKER_CONCURRENCY
JOB_MAX_RETRIES
```

## Observability

```text
SENTRY_DSN / equivalent
OTEL_EXPORTER_ENDPOINT
METRICS_ENDPOINT
```

## Feature flags

Use controlled feature flags for:
- semantic duplicate detection.
- user-selectable AI models.
- new parsers.
- new question types.
- experimental student features.

## Environment separation

Production secrets must never be reused in staging or development.
