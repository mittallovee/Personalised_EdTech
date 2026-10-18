# Local Development Plan

18 October 2026. **Confirmed target: this PC.** Everything below is a proposed setup plan; no installation, service launch or application code has been performed.

## Proposed topology

Use Linux containers through Docker Desktop/WSL2 if local prerequisites and applicable licensing fit. Alternative: isolated Linux services in WSL2 after checking feasibility. Celery's official documentation does not support native Windows; do not advertise that path as verified.

| Component | Proposed development responsibility |
| --- | --- |
| Web | Next.js faculty/admin UI and common app entry |
| API | FastAPI modular service; auth/tenant/grant checks and typed contracts |
| PostgreSQL | Durable content, workflow, jobs, budgets, audit and manifests |
| Redis | Broker/cache, not sole durable job state |
| Linux worker | Parsing, OCR, pattern learning/reuse, AI, copying and asset tasks |
| Private asset store | Persistent local directory/volume behind storage interface; no user-supplied disk paths |
| Local configuration | Server-only secrets and separate encryption key, excluded from repository/archive |

Bind local web/API to loopback by default. Internal database/broker remain private. Ports, version pins, allocated memory and optional development tooling are chosen after read-only machine/runtime compatibility checks at implementation. No public tunnel, router changes, domain purchase or cloud provisioning is required by local hosting.

Local hosting does not mean AI is offline: configured coaching-owned provider APIs require network access and may incur their own charges. SMS OTP and Google login likewise require real external configuration for complete flows. Do not label mocks as completed integrations.

## Persistent data and restart behavior

Database data, originals, required assets and backup manifests live outside disposable application containers. Queue loss/restart reconciles durable SQL jobs/checkpoints. Stopping the PC interrupts active work; next startup reports interrupted attempts and uses idempotent retry rather than pretending uninterrupted service.

Use independent disposable test databases and synthetic fixtures. Never run migration-reset/test deletion against real question data. Propose a development database name/environment guard and explicit backup before migration of valued data.

## Backup/recovery proposal

Daily logical DB export plus consistent asset/checksum manifest and required-file copy; retain proposed 7 daily and 4 weekly sets, plus pre-migration checkpoint. Keep the encryption key recoverable separately from encrypted data. Protect backups because they contain coaching content and encrypted credential records.

A copy on the same disk alone does not protect against PC loss. Before relying on real imported data, choose an encrypted off-machine destination and demonstrate isolated restore of DB, assets and configuration references. No backup has been created or restored and no RPO/RTO is promised.

## Implementation gates

1. Review this document package and proposed first slice.
2. Inspect installed runtimes, virtualization, available resources and supported versions; record exact findings.
3. Implement only the agreed first slice, with no live-provider calls needed for foundation.
4. Verify local startup/restart, migration, tenant denial and immutable publication in disposable fixtures.
5. Add real authentication/provider/recognition integrations through later release-one slices and evaluate samples when supplied.

Production hosting/domain/monthly infrastructure budget, remote access, uptime/recovery guarantees and operational policy remain later deployment decisions. No host account or spending authority is inferred.
