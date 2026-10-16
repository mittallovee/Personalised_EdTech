# Multi-SaaS Question Management & Content Platform

## Documentation Pack

This documentation pack is the implementation baseline for the coaching Question Bank / Content Management Platform discussed so far.

## Product summary

A multi-tenant SaaS platform for coaching organizations to ingest, create, enrich, validate, version, search, and publish academic questions and supporting content.

Initial focus:
- Physics for IIT-JEE / NEET and Class IX-XII.
- PDF/DOC/DOCX ingestion.
- Structured question bank with rich metadata.
- Master Question + Variant + Version model.
- Human review and approval workflow.
- AI-assisted tagging, generation, modification, translation, solution generation, diagrams, and duplicate detection.
- AI model selection through an AI gateway/orchestrator.
- Test Builder for assembling tests from approved/published questions.

Future expansion:
- Other subjects, exams, curricula, languages, organizations, and student-facing analytics/personalization.

## Recommended reading order

1. `01-vision-and-scope.md`
2. `02-system-architecture.md`
3. `03-roles-permissions.md`
4. `04-functional-requirements.md`
5. `05-question-domain-model.md`
6. `06-database-schema.md`
7. `07-question-ingestion.md`
8. `08-ingestion-qc.md`
9. `09-content-review-workflow.md`
10. `10-ai-platform.md`
11. `11-ai-prompts-and-provenance.md`
12. `12-search-and-duplicate-detection.md`
13. `13-test-builder.md`
14. `14-api-specification.md`
15. `15-frontend-application.md`
16. `16-security-and-multi-tenancy.md`
17. `17-storage-and-media.md`
18. `18-observability-and-operations.md`
19. `19-testing-and-quality.md`
20. `20-devops-deployment.md`
21. `21-data-governance.md`
22. `22-roadmap-and-delivery.md`
23. `23-architecture-decisions.md`
24. `24-engineering-standards.md`
25. `25-analytics-and-future-student-layer.md`

## Definition of done for MVP

The MVP is complete when an organization can:

1. Sign in and operate inside an isolated tenant.
2. Upload a PDF/DOC/DOCX ingestion batch.
3. Extract and segment questions into staging records.
4. Review extraction against the original source.
5. Create a new Master Question, attach to an existing Master, mark duplicate, or create a Variant.
6. Edit structured question content, solutions, diagrams, and metadata.
7. Send content through Creator → Reviewer → Approver → Published lifecycle.
8. Preserve immutable published versions and a complete audit trail.
9. Search/filter the approved question bank.
10. Build a test using metadata and content-availability filters.
11. Track AI model/prompt provenance for every AI operation.
12. Operate reliably with monitoring, backups, security controls, and CI/CD.
