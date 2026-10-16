# 31. Database Migration Plan

## Migration philosophy

Schema changes should be incremental, observable, and reversible where practical.

## Initial migration sequence

1. Organizations/users/memberships.
2. Roles/permissions.
3. Taxonomy foundation.
4. Master/Variant/Version.
5. Sources/assets.
6. Ingestion.
7. Review/audit.
8. AI registry/jobs.
9. Tests.
10. Search indexes.

## Expand/contract pattern

Example: renaming a field.

```text
Migration A: add new field
Migration B: application writes both
Migration C: backfill
Migration D: application reads new field
Migration E: remove old field
```

Avoid destructive one-step migrations during active production traffic.

## Seed data

Development/staging seed data may include:
- sample organization.
- sample roles.
- sample taxonomy.
- demo AI actions/models.
- synthetic questions.

Never seed real production API keys or private source content.

## Index rollout

On large PostgreSQL tables, evaluate concurrent index creation where appropriate to avoid locking writes.

## Data integrity checks

Before destructive or structural migration:
- count affected rows.
- check orphaned foreign keys.
- validate duplicate public IDs.
- validate status invariants.

## Rollback

Document rollback per migration. If true rollback is unsafe because data transformation is irreversible, use a compensating migration instead.
