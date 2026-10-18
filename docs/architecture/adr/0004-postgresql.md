# ADR-0004: PostgreSQL as system of record; SQLAlchemy 2 + Alembic
- Status: Proposed · Date: 2026-10-18
## Context
Relational data with strong integrity (questions, versions, reviews, grants), JSON content blocks, full-text/fuzzy search and later embeddings. Must run locally and on managed cloud databases.
## Decision
PostgreSQL (latest stable supported by AWS RDS and Google Cloud SQL at M1/M7). Extensions: `pg_trgm` (P1), `pgvector` (P2). JSONB only for versioned content blocks and snapshots; everything queried by filters is a real column. Access via SQLAlchemy 2 (typed), migrations via Alembic.
## Consequences
+ One database for data, search, jobs; managed offerings on all clouds.
− JSONB content needs schema validation in the app (Pydantic, `schema_version` field).
## Alternatives
MongoDB (weak relational integrity), separate search engine now (premature).
