# Backup and restore

> Requirement **K-03** (tooling and the restore drill), N-06 · Decision: [ADR-0017](../architecture/adr/0017-backups-and-restore.md)
> **Not done yet:** real scheduled, off-machine backups and a restore of real data. That is requirement **K-16**,
> due before the first real coaching uses the app (M4). Until then the tooling exists and is tested, but nothing
> runs it for you.

## What is protected

| What | By what | Status |
|---|---|---|
| The database: every coaching's data, accounts, sessions, audit log | `infra/scripts/backup-db.sh` | Tooling done and tested (K-03) |
| Uploaded files (images, documents), from M3 PR 3g on | the storage backend's own copy | Planned with K-16 |
| Settings and secrets (`.env`, keys) | your password manager; never in Git | Yours to keep safe |
| The code | Git | Done |

## Targets (proposed; the owner confirms)

| | P1 on your PC | From M7 on managed PostgreSQL |
|---|---|---|
| **Data we may lose** (RPO) | up to **24 hours** (one daily backup) | up to **5 minutes** (point-in-time recovery) |
| **Time to be working again** (RTO) | within **4 hours** from backup files | within **1 hour** |
| **How long copies are kept** | 14 daily, 8 weekly, 6 monthly | the provider's setting, same dump kept |
| **Where copies are kept** | one copy off the machine and outside the same account (K-16) | same |

The 4-hour figure is a guess until K-16 measures a restore of real data; the drill below restores a small test database in seconds.

## The one rule about who takes the backup

Every table holding a coaching's data has **forced row-level security**. A database role that row-level security
filters (like `qbank_app` or `qbank_worker`) cannot take a complete backup: it gets an error or, worse, a file with
rows missing. So the backup must be taken by a **superuser or a role with `BYPASSRLS`**:

- locally, the `POSTGRES_USER` of the compose stack (`qbank_owner`) is a superuser, and is what you use;
- in the cloud, create a dedicated `qbank_backup` role with `BYPASSRLS` and read access, used for nothing else.

`backup-db.sh` checks this first and refuses to run with any other role.

## Take a backup

From the repository root, with the compose stack up (`docker compose up -d`):

```bash
mkdir -p backups
set -a; . ./.env; set +a
PGHOST=localhost PGUSER="$POSTGRES_USER" PGPASSWORD="$POSTGRES_PASSWORD" PGDATABASE="$POSTGRES_DB" \
  PG_DOCKER_IMAGE=postgres:17 \
  infra/scripts/backup-db.sh "backups/qbank-$(date +%F-%H%M).dump"
```

This writes the backup file and a `.sha256` file beside it, both readable only by you. `PG_DOCKER_IMAGE` runs
`pg_dump` from a Docker image of the **same PostgreSQL version as the server** (a dump tool older than the server
refuses to run); leave it out if the tools on your machine already match. The `backups/` folder is ignored by Git.
**Backups contain personal data.** Treat them like the database itself, and move a copy off the machine (K-16).

## Restore a backup

A restore always goes into a **new** database. It never overwrites, so a mistaken restore cannot destroy data.

```bash
# 1. On a brand-new server only: create the roles the backup grants privileges to. That is always
#    qbank_app and qbank_worker (infra/db/ensure-app-role.sh does both; the compose stack's db-init
#    service already did it on yours), and any other role you gave access, such as a backup role with
#    its own SELECT grants. The script checks first and, if one is missing, lists it and stops before
#    restoring anything. It also stops if qbank_worker is not a member of qbank_app (a backup cannot carry
#    memberships; ensure-app-role.sh sets it): the restored worker would otherwise fail on every table.
# 2. Restore beside the old database:
PGHOST=localhost PGUSER="$POSTGRES_USER" PGPASSWORD="$POSTGRES_PASSWORD" PG_DOCKER_IMAGE=postgres:17 \
  infra/scripts/restore-db.sh backups/qbank-2026-10-23-1030.dump qbank_restored
```

The script checks the file against its checksum first and stops if it does not match. The new database gets the old one's
encoding and locale, its `ALTER DATABASE ... SET` settings (also those set for one role in it) and its connect permissions, which the backup carries, and not
this server's defaults. (The database comment is not restored.) It stops at the first error and leaves a half-restored
database in place so you can look at it.

To **switch to the restored copy**: stop the API and the worker, point `DATABASE_URL` and the worker's URL at
`qbank_restored`, start them, sign in and look around. Keep the old database until you are sure; drop it later.

## The restore drill (runs on every change)

`services/api/tests/integration/test_backup_restore.py`, part of the Backend job in CI, runs the real scripts
against the migrated test database with two coachings in it, and then checks that the restored copy has the same:

- tables, columns, indexes, constraints and database functions, and migration version;
- number of rows in every table;
- row-level-security switches and policies;
- privileges of `qbank_app` and `qbank_worker`, including what each can really do through its memberships;

and that, signed in as the runtime role, coaching A sees only coaching A, coaching B only B, and no coaching
context sees nothing. It also checks the safety rules: a role that cannot bypass row-level security is refused, a
restore never overwrites, a damaged file is refused, and a backup that grants privileges to a role the new server
does not have stops with the role's name before anything is created (and restores once the role exists), so does a server
where `qbank_worker` is not a member of `qbank_app`. A separate test restores a database with a different locale, a
setting and a connect permission, and checks the copy has the same.

I checked that the drill has teeth by breaking the scripts five ways (leaving out the privileges, leaving out one
table's rows, removing the role check, removing the membership check, ignoring the database properties); the drill
failed each time with a message naming what differed.

Run it yourself (needs PostgreSQL as described in the test setup, and `pg_dump` matching the server or
`PG_DOCKER_IMAGE`):

```bash
cd services/api && uv run pytest tests/integration/test_backup_restore.py
```

If it fails, **do not weaken the drill**: it means a restored database would differ from the original in something
listed above, and the difference is the thing to understand.

## Known limits

- A logical dump takes longer as the data grows; managed point-in-time recovery (M7) removes that limit.
- Everything in the database comes back as it was in the backup, including sign-in sessions, one-time links (with their original expiry times) and the background job queue. After a restore, check the job list before you trust that queued work will run again.
- Files and secrets are not in the dump (see the table at the top).
