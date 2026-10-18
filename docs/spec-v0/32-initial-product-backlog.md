# 32. Initial Product Backlog

## P0 — Must have

### Foundation
- [ ] Repository setup.
- [ ] Authentication.
- [ ] Organization/membership.
- [ ] RBAC.
- [ ] PostgreSQL migrations.
- [ ] Object storage.
- [ ] CI/CD baseline.

### Question bank
- [ ] Master Question.
- [ ] Variant.
- [ ] Version.
- [ ] Structured content editor.
- [ ] Answers by question type.
- [ ] Solutions.
- [ ] Taxonomy.
- [ ] Source attribution.
- [ ] Draft/review/approved/published.
- [ ] Audit history.

### Ingestion
- [ ] Batch creation.
- [ ] PDF/DOC/DOCX upload.
- [ ] File validation/scanning.
- [ ] Extraction pipeline.
- [ ] Segmentation.
- [ ] Asset extraction.
- [ ] Ingestion QC.
- [ ] New/Existing/Variant/Duplicate decisions.

## P1 — High value

- [ ] AI model registry.
- [ ] AI gateway.
- [ ] Prompt registry.
- [ ] AI tagging.
- [ ] AI verification.
- [ ] Model selection UI.
- [ ] Search.
- [ ] Fuzzy duplicate detection.
- [ ] Semantic duplicate detection.
- [ ] Bulk review operations.
- [ ] Test Builder.

## P2 — Scale / advanced

- [ ] Advanced blueprint engine.
- [ ] Local model fleet management.
- [ ] Advanced analytics.
- [ ] Student layer.
- [ ] Personalized recommendations.
- [ ] Dedicated search service if required by benchmarks.

## Delivery slices

### Slice 1
Login + organization + question CRUD.

### Slice 2
Versioning + review + audit.

### Slice 3
PDF ingestion + staging.

### Slice 4
Ingestion QC + commit.

### Slice 5
AI gateway + tagging.

### Slice 6
Search + duplicates.

### Slice 7
Test Builder.

Each slice must be deployable and tested independently.
