# 23. Architecture Decision Records

## ADR-001: Modular monolith first

**Decision:** Start as a modular monolith with explicit domain boundaries.

**Reason:** Faster iteration while the domain is evolving; easier transactions and debugging. Extract heavy workers/services later.

## ADR-002: Master Question identity

**Decision:** Use a permanent opaque Master Question ID.

**Reason:** Taxonomy, language, wording, and versions change independently of conceptual identity.

## ADR-003: Version immutability

**Decision:** Published versions are immutable.

**Reason:** Reproducibility, auditability, and test integrity.

## ADR-004: Variant as separate entity

**Decision:** Variants are separate from versions.

**Reason:** A variant is a distinct usable question derived from the same Master; versions represent revisions of that variant.

## ADR-005: Ingestion staging

**Decision:** Raw extraction does not write directly to production Question Bank records.

**Reason:** Extraction is fallible and requires human QC.

## ADR-006: AI gateway abstraction

**Decision:** Application calls an AI orchestrator and gateway, not providers directly.

**Reason:** Model portability, centralized credentials, policy, cost tracking, and local-model support.

## ADR-007: User-selectable AI models

**Decision:** Users may select among platform-approved models for actions that allow selection; each action has a default.

**Reason:** Balances ease of use and expert control.

## ADR-008: AI provenance

**Decision:** Store exact model version and prompt version for every content-changing AI job.

**Reason:** Explainability and auditability.

## ADR-009: Source separate from question identity

**Decision:** Source is an independent relationship.

**Reason:** One question may have many sources, while one source may contain many questions.

## ADR-010: PostgreSQL-first search

**Decision:** Use Postgres FTS/trigram initially and add a dedicated engine only when measured needs justify it.

**Reason:** Reduces early operational complexity.

## ADR-011: Test publication snapshot/hash

**Decision:** A published test is immutable and reproducible even if source question content later changes.

**Reason:** Exam/test integrity.

## ADR-012: Configuration over hard-coded domain policy

**Decision:** Allowed email domains, model availability, AI defaults, and workflow settings are configuration/policy data.

**Reason:** Multi-SaaS flexibility.
