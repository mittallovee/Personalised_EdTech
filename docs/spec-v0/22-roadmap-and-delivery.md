# 22. Roadmap and Delivery Plan

## Phase 0 — Foundations

- Repository structure.
- TypeScript conventions.
- Authentication.
- Organization model.
- RBAC.
- Database migrations.
- Object storage.
- CI/CD.
- Logging/monitoring baseline.

## Phase 1 — Question Bank Core

Deliver:
- Master Question.
- Variant.
- Version.
- Manual question creation.
- Structured content editor.
- Metadata/taxonomy.
- Source attribution.
- Draft/review/approved/published states.
- Audit trail.

## Phase 2 — Ingestion

Deliver:
- Batch upload.
- PDF/DOC/DOCX parsing.
- Question segmentation.
- Asset extraction.
- Ingestion staging.
- Ingestion QC workspace.
- Create Master/Existing/Variant/Duplicate decisions.

## Phase 3 — AI Platform

Deliver:
- AI model registry.
- AI action registry.
- LiteLLM gateway integration.
- Prompt versioning.
- AI job orchestration.
- Model selection UI.
- Cost/usage tracking.
- AI provenance.

## Phase 4 — Search and Duplicate Detection

Deliver:
- Full text.
- Fuzzy search.
- Candidate duplicate detection.
- Semantic similarity.
- Review workflow for duplicates.

## Phase 5 — Test Builder

Deliver:
- Question filters.
- Live counts.
- Solution/video filters.
- Master/variant rules.
- Draft tests.
- Published test versions.

## Phase 6 — Hardening

- Performance.
- Security.
- Backup/restore.
- Observability.
- Bulk operations.
- UX optimization.

## Phase 7 — Student layer

- Test delivery.
- Attempts.
- Timing.
- Answer analytics.
- Concept analytics.
- Personalized recommendations.

## Recommended first usable milestone

Do not wait for every AI capability.

The first operational milestone should be:

```text
Login
 -> Upload PDF
 -> Extract questions
 -> Review
 -> Create Draft
 -> Review
 -> Approve
 -> Publish
 -> Search
```

That is the point at which real content entry can begin at scale.
