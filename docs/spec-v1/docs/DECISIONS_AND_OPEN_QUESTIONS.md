# Decisions and Deferred Questions

Consolidated 18 October 2026. Read [master context](PROJECT_MASTER_CONTEXT.md), [decision register](PRODUCT_DECISION_REGISTER.md) and [roadmap](IMPLEMENTATION_ROADMAP.md) together.

## Current status

The current requirements interview is closed: **zero required user questions remain**. User has authorized document consolidation. No application implementation is underway.

Confirmed first-release direction includes one initial coaching/multi-coaching architecture, all nine question formats, admin-defined permissions, AI-managed taxonomy, all agreed AI tools, background ingestion, adaptive extraction patterns, independent platform-managed educational copying, in-app-only notifications, the four initial AI providers and local development hosting on this PC.

See [PRD](PRD.md) and [requirements traceability](REQUIREMENTS_TRACEABILITY.md) for coverage. Proposed technical decisions are concrete in [technical defaults](TECHNICAL_DESIGN_PROPOSALS.md), not a new questionnaire.

## Design proposals ready for review

| Concern | Proposed disposition | Reference |
| --- | --- | --- |
| Stack/local services | Modular monolith, PostgreSQL, API/web, Linux workers on this Windows PC, private filesystem abstraction | Architecture/local plan |
| Identity | Canonical verified methods, opaque server sessions, explicit verified account linking | Identity |
| Content | Versioned rich blocks, typed answer unions, stable option/item IDs and exact decimal strings | Schema/examples |
| Drafts/QC | Immutable draft revisions and revision-bound review/approval/publication; edits invalidate prior current approvals | Lifecycle |
| Global codes | Uppercase eight-character A–Z/0–9, secure generator/unique constraint/non-reuse | Technical defaults |
| API | Versioned routes, authenticated tenant context, cursor paging, ETags and idempotency | API contracts |
| Jobs | Durable DB state, checkpoints, bounded transient retry, cooperative cancel | Jobs |
| Pattern lifecycle | Candidate → usable/deprecated/disabled, coverage validation and isolated AI fallback | Patterns |
| Copy conflicts | Independent import namespace and new identities; block unresolved conflicts rather than overwrite target work | Copy specification |
| Operations | Local persistence, proposed backups, later restore verification and production sizing | Local plan/security |

Engineering may refine these proposals using implementation evidence without changing confirmed product policy. A consequential product conflict must be surfaced with its reason.

## Explicitly deferred

- Source samples, representative OCR/handwriting/format benchmarks, token/time savings and lakh-scale measurements: before claiming engine quality/capacity, not before documentation.
- Production hosting, domain, paid infrastructure budget, availability/recovery goals, privacy/retention obligations and operational service choices: before hosted deployment.
- Exact live model IDs/capabilities/prices/data handling: verify before enabling an integration; no secret keys requested in chat.
- OAuth/OTP delivery credentials and recovery execution: before real external authentication, without adding notification emails.
- Test builder/scoring/export; student enrollment/attempts/analytics/recommendations; subscription/payments; courses/live/recorded delivery and AI teaching/videos: before the relevant later milestone.

## Review boundary

Documents can be complete enough for review while runtime compatibility and empirical targets remain unverified. Do not describe this package as an implemented system or approved production deployment. The historical interview is retained separately; active documents use the latest confirmed policy.
