# ADR-0017: Backups: logical dumps with a tested restore now; managed point-in-time recovery from M7
- Status: Proposed · Date: 2026-10-23 · Requirements: K-03, K-16, N-06
## Context
Every coaching's question bank lives in one PostgreSQL database with forced row-level security (ADR-0005).
Losing it, or restoring a copy that quietly lost a protection, would be the worst outcome for the platform.
Until M7 the database runs on the owner's PC; after M7 it moves to a managed PostgreSQL (ADR-0013).
## Decision
- **Now (P1, M1–M6):** a logical backup with `pg_dump` in custom format (`infra/scripts/backup-db.sh`), restored
  with `pg_restore` into a **new** database, never over an existing one (`restore-db.sh`).
- The backup role must be a superuser or have `BYPASSRLS`; the script refuses any other role, because a dump by
  a role that row-level security filters would look complete and not be.
- A **restore drill runs in CI on every change** (`tests/integration/test_backup_restore.py`): back up, restore,
  compare structure, row counts, policies and privileges, and prove tenant isolation still holds in the copy.
- A checksum file beside each backup detects damage; the file is written with mode 600.
- **From M7:** the provider's managed backups with point-in-time recovery become the primary protection, and the
  dump stays as a portable, provider-independent second copy.
- Real scheduled, off-machine copies and a restore of real data are requirement K-16, before the first real use (M4).
## Consequences
+ Simple, readable, works the same on a PC, in CI and in the cloud; the drill keeps it honest.
+ Restoring beside the old database means a mistaken restore cannot destroy data.
− A daily dump loses up to a day of changes (the target for P1; see the operations document).
− Dump and restore time grow with the data; the point-in-time recovery from M7 removes that limit.
## Alternatives considered
- **Physical base backups with WAL archiving** (pgBackRest, Barman): point-in-time recovery on our own server, but
  several moving parts to run and test on a PC; the managed service gives this at M7 for free.
- **Volume or disk snapshots:** fast, but not portable between providers and not checked for tenant protections.
