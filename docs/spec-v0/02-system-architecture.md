# 2. System Architecture

## Architecture style

Use a modular monolith for the initial implementation with clean module boundaries, while designing module contracts so high-load components can be extracted into services later.

This is preferable to prematurely operating many microservices while the domain model is still evolving.

## Logical architecture

```text
Web App (Next.js / React)
        |
        v
API / Application Layer
        |
        +-----------------------+
        |                       |
        v                       v
Content Modules            AI Orchestrator
        |                       |
        v                       v
PostgreSQL                LiteLLM / AI Gateway
        |                       |
        v                       +----------------------+
Object Storage             External / Local Models

Async jobs / workers
        |
        +--> ingestion
        +--> OCR/extraction
        +--> document parsing
        +--> asset processing
        +--> AI jobs
        +--> duplicate indexing
        +--> exports
```

## Core modules

1. Identity & access.
2. Organization / tenancy.
3. Taxonomy.
4. Question Bank.
5. Question Versioning.
6. Source & ingestion.
7. Review / QC.
8. AI platform.
9. Search / duplicate detection.
10. Media/assets.
11. Test Builder.
12. Audit / activity.
13. Notification/task system.
14. Reporting / analytics.

## Suggested implementation stack

- Frontend: Next.js + React + TypeScript.
- Backend: TypeScript application layer; REST API initially.
- Database: PostgreSQL, with JSONB only where schema flexibility materially helps.
- Object storage: S3-compatible storage or Supabase Storage.
- Search: PostgreSQL FTS/trigram for MVP; dedicated search engine later if needed.
- AI gateway: LiteLLM or equivalent model routing layer.
- Async processing: durable job queue backed by Redis/Postgres/SQS-compatible infrastructure.
- Authentication: email/password plus Google OAuth as configured by organization/platform policy.
- Containers: Docker.
- Deployment: EC2 initially; Kubernetes when operational scale justifies it.
- IaC: Terraform.
- Automation: n8n for non-critical integrations/operations where useful; core transactional workflows stay in the application.

## Environments

- Local.
- Development.
- Staging.
- Production.

Never allow development/staging jobs to write to production databases or production object buckets.

## Data flow: question lifecycle

```text
Source file
 -> ingestion batch
 -> extraction item
 -> ingestion review
 -> master/variant/version
 -> content review
 -> approved
 -> published
 -> test usage
```

## Data flow: AI

```text
Application action
 -> AI job
 -> policy/config resolver
 -> selected model
 -> AI gateway
 -> provider/local model
 -> raw response
 -> schema validation
 -> normalized result
 -> application transaction
 -> provenance/audit
```

## Architecture constraints

- No business logic in the browser that bypasses server authorization.
- Never trust client-supplied organization IDs.
- Every mutating endpoint must be authorization-checked server-side.
- Published content is append-only through new versions.
- Long-running ingestion and AI tasks are asynchronous.
