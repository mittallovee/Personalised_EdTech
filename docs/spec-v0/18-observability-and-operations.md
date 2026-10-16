# 18. Observability and Operations

## Logging

Structured JSON logs should include:
- timestamp.
- service/module.
- level.
- requestId.
- userId when appropriate.
- organizationId when appropriate.
- entityId.
- operation.
- duration.
- result/error code.

Never log secrets or full sensitive question content by default.

## Metrics

### API
- request count.
- latency.
- 4xx/5xx rate.
- endpoint saturation.

### Ingestion
- files processed.
- questions detected.
- extraction success rate.
- low-confidence rate.
- queue age.
- retries.

### AI
- jobs by action.
- success/failure rate.
- latency.
- tokens.
- estimated cost.
- model utilization.
- fallback frequency.

### Review
- backlog.
- questions reviewed/day.
- median review time.
- rejection rate.
- dispute rate.

## Tracing

Propagate request/job IDs through:

```text
Browser -> API -> Worker -> AI Gateway -> Provider
```

## Queue operations

Workers must support:
- retries.
- exponential backoff.
- dead-letter queue.
- idempotency.
- cancellation where safe.

## Alerts

Recommended alerts:
- API error spike.
- ingestion backlog above threshold.
- queue stalled.
- AI provider outage.
- cost budget exceeded.
- storage failures.
- database connection exhaustion.

## Backups

Minimum production plan:
- Automated database backups.
- Point-in-time recovery where supported.
- Object versioning for critical source buckets.
- Periodic restore tests.

## Operational dashboards

Create dashboards for:
- System health.
- Ingestion.
- AI.
- Review operations.
- Database/storage.
