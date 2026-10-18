# 20. DevOps and Deployment

## Initial deployment

Recommended early topology:

```text
Internet
   |
CDN / WAF / DNS
   |
Reverse Proxy / Load Balancer
   |
Next.js + API
   |
PostgreSQL
   |
Object Storage

Async Workers
   |
Queue

AI Gateway
   |
Models / Providers
```

EC2 can be used initially where operational simplicity is more important than cluster complexity.

## Docker

Build separate images when useful:
- web/app.
- worker.
- AI gateway.

Keep images minimal and non-root where practical.

## CI/CD

Pipeline:

```text
Commit
 -> lint
 -> typecheck
 -> unit tests
 -> integration tests
 -> build
 -> security/dependency scan
 -> container build
 -> staging deploy
 -> smoke tests
 -> production approval/deploy
```

## Database migrations

Use migration files checked into version control.

Rules:
- Backward-compatible migration first where zero-downtime matters.
- Deploy application supporting old + new schema.
- Backfill.
- Switch reads/writes.
- Remove old schema later.

## Infrastructure as code

Use Terraform for:
- networking.
- compute.
- storage.
- database.
- secrets integration.
- observability.

## Environments

Separate:
- credentials.
- databases.
- storage.
- AI gateway configuration.

## Scaling

Scale workers independently for:
- document parsing.
- OCR/extraction.
- AI jobs.
- duplicate embedding jobs.
- export jobs.

## Kubernetes migration trigger

Consider Kubernetes when:
- worker fleets become numerous.
- multiple environments require repeatable cluster operations.
- autoscaling complexity becomes material.
- deployment/service isolation benefits outweigh ops cost.

Do not adopt Kubernetes merely because the architecture is “microservices-ready”.

## Disaster recovery

Document:
- RPO.
- RTO.
- restore steps.
- database recovery.
- object restoration.
- secret re-provisioning.
- DNS failover.

Run restoration drills.
