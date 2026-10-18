# Background Jobs and Cancellation

Consolidated 18 October 2026. Confirmed: processing runs in background; faculty can upload again/navigate/do other work; faculty can cancel own jobs; keep extracted drafts and any reviewed/published content. Proposed mechanics follow.

## Durable execution

Persist jobs, attempts, stage checkpoints, source/input revision hashes and output mappings in PostgreSQL. Queue contains references, not sole state. Proposed heavy-worker concurrency begins at 1 and is configurable after measurement; accepted work can queue without blocking ordinary application use.

States: QUEUED → RUNNING → SUCCEEDED/PARTIAL/FAILED. Cancellation uses CANCEL_REQUESTED before CANCELLED. BLOCKED records actionable missing configuration/budget/context; it is not success. Each stage tracks completed/total with explicit units or null total.

Persist completed outputs and stage events transactionally. Unique job+stage+input+output keys make dispatch/retry idempotent. Broker delivery is not assumed exactly once.

## Retry and recovery proposal

Transient eligible failures retry with bounded delay/attempts (P-21); auth/schema/role failures do not blindly loop. Retry/resume uses checkpoints and output mappings, preserving human corrections and existing identities. Explicit retry of a cancelled job uses a linked new attempt/execution without erasing its cancellation history.

On PC restart, interrupted attempts are visible and reconciled with durable checkpoints. A queue reconnect must not repeat billable work or materialize duplicates blindly; provider request IDs/evidence determine ambiguous in-flight disposition.

## Cancellation

Current actor cancels own job; admin/platform broader job administration remains. Verify tenant/job/current state/revision before recording request. Cooperative checkpoints stop future parsing/provider dispatch/materialization. Already in-flight calls may complete/cost money; show requested versus acknowledged cancellation honestly.

Keep completed unpublished candidates as drafts with sources/warnings, do not delete originals or demote published/reviewed work. Completed approved/reviewed work remains stable; only unfinished stage results are marked unprocessed/cancelled. Completion/cancel race is resolved transactionally, with one truthful terminal outcome.

## Authority and evidence

Before protected output writes/provider calls recheck current actor/membership/grants, tenant, revision, cancellation and budget. Losing access stops future unauthorized work but preserves existing organization data/history.

Status APIs survive navigation and expose safe errors/per-file partial results. Unknown denominators never produce fake progress percentages. No worker, restart, retry or cancellation tests have run.

[Ingestion](QUESTION_INGESTION_PIPELINE.md), [API](API_CONTRACTS_DRAFT.md), [local plan](LOCAL_DEVELOPMENT_PLAN.md).
