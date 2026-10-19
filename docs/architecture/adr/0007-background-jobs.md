# ADR-0007: PostgreSQL-backed job queue behind our own interface
- Status: **Accepted** (owner, 18 Oct 2026) · Date: 2026-10-18
## Context
Uploads, extraction, AI runs, translation, model-catalogue refresh must run in the background, survive restarts, retry safely and be cancellable. Small team; Windows PC for development.
## Decision
- Our own **job records** in PostgreSQL (`jobs`, `job_attempts`, checkpoints, output mappings) are the source of truth for status/progress/cancel.
- Dispatch uses a **PostgreSQL-backed queue library** (candidate: Procrastinate; final pick at M1 after checking maintenance status), wrapped in `core/jobs.py` so it can be swapped.
- Handlers are idempotent (unique output keys); retries bounded with backoff; cooperative cancellation.
## Consequences
+ No Redis/broker to run; enqueue happens in the same transaction as the data change (no lost jobs).
− Lower peak throughput than Redis-based queues; acceptable for Phase 1–2 volumes. Revisit with measurements (Celery/Redis or cloud queue) if needed.
## Alternatives
Celery + Redis (more moving parts; native Windows unsupported). Cloud queues (SQS/Pub/Sub; not available locally).

## Implementation note (M1 PR 4, 18 Oct 2026)
The "final pick at M1" is **our own small queue on the `jobs` table** rather than Procrastinate. Reasons: our
`jobs` table already had to be the durable source of truth (state, progress, cancel); a library would add a
second set of job tables; and claiming across coachings needs narrow database functions so the runtime
role stays tenant-restricted. The mechanism is the standard PostgreSQL pattern: `SELECT … FOR UPDATE SKIP
LOCKED` to claim, a lease (`locked_until`) renewed in the background while a job runs (a heartbeat) so only
crashed workers lose their jobs, bounded retries with backoff. About 300 lines in `core/jobs.py` and
migration 0003. The decision above (PostgreSQL, not Redis) is unchanged.
