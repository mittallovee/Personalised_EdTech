# ADR-0005: Tenant isolation — RLS + service checks + composite keys
- Status: Proposed · Date: 2026-10-18
## Context
Many coachings share one database. A leak of one coaching's questions to another is the worst possible failure.
## Decision
Defence in depth:
1. **Service layer**: the Principal's coaching is resolved server-side; every query is scoped.
2. **PostgreSQL Row Level Security** on every tenant-owned table, `FORCE ROW LEVEL SECURITY`, policy `organization_id = current_setting('app.org_id', true)::uuid`. Each transaction runs `SET LOCAL app.org_id`. Missing setting gives NULL, which returns zero rows (fails closed).
3. **DB roles**: `qbank_owner` owns tables and runs migrations; the runtime role `qbank_app` is not owner, not superuser, no `BYPASSRLS`.
4. **Composite foreign keys** `(organization_id, id)` so cross-coaching references are impossible even with known IDs.
5. **Platform admin** acts inside one target coaching at a time (sets `app.org_id` to it), audited. Platform-wide tables (organizations list) use a separate `app.is_platform` policy.
6. Two-coaching isolation tests for every tenant-owned table, in CI.
## Consequences
+ A forgotten WHERE clause cannot leak data.
− Slightly more complex connection handling (context per transaction); tests required.
## Alternatives
Database per tenant (heavy ops at many coachings), app-only checks (one bug = leak).
