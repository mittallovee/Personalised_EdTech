# ADR-0008: Search and duplicate detection inside PostgreSQL
- Status: Proposed · Date: 2026-10-18
## Context
Bank of lakhs of questions per coaching in 7 languages; filters with counts; free-text and typo-tolerant search; duplicate detection; later "find similar".
## Decision
- Filters/counts: indexed columns per tenant, measured on a 1-lakh synthetic fixture.
- Free text: PostgreSQL full-text search on a normalized text column (`simple` configuration, since Postgres has no stemmers for Indian languages) + **pg_trgm** for fuzzy matching.
- Duplicates P1: normalized-content hash (exact) + trigram similarity (near); human decides.
- P2: **pgvector** embeddings for semantic similarity.
- Revisit a dedicated engine (OpenSearch etc.) only if measurements fail targets.
## Consequences
+ No extra infrastructure; tenant isolation via RLS applies to search too.
− Ranking is simpler than a dedicated search engine.
