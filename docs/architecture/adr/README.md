# Architecture Decision Records (ADRs)

One file per significant decision: **context → decision → consequences → alternatives**.
An accepted ADR is never edited to change its meaning. A new ADR **supersedes** it.
Status values: `Proposed` → `Accepted` (owner approved) → `Superseded by ADR-xxxx`.

| ADR | Decision | Status |
|---|---|---|
| [0001](./0001-record-decisions.md) | Record architecture decisions as ADRs | Proposed |
| [0002](./0002-modular-monolith.md) | Modular monolith with a separate worker process | Proposed |
| [0003](./0003-tech-stack.md) | Python/FastAPI backend, Next.js/TypeScript web, monorepo | Proposed |
| [0004](./0004-postgresql.md) | PostgreSQL as system of record; SQLAlchemy 2 + Alembic | Proposed |
| [0005](./0005-tenant-isolation.md) | Tenant isolation: RLS + service checks + composite keys | Proposed |
| [0006](./0006-api-first-multi-client.md) | API-first REST, OpenAPI contract, pluggable auth for many clients | Proposed |
| [0007](./0007-background-jobs.md) | PostgreSQL-backed job queue behind our own interface | Proposed |
| [0008](./0008-search-in-postgres.md) | Search and duplicate detection inside PostgreSQL | Proposed |
| [0009](./0009-ai-platform.md) | AI provider adapters, live model catalogue, prompt library | Proposed |
| [0010](./0010-observability.md) | Structured logs + OpenTelemetry + Sentry | Proposed |
| [0011](./0011-identifiers.md) | UUIDv7 internal IDs + 8-character question codes | Proposed |
| [0012](./0012-file-storage.md) | Storage interface: local disk → S3/GCS | Proposed |
| [0013](./0013-cloud-neutral-deployment.md) | Containers, cloud-neutral; cloud choice at M7 | Proposed |
