# ADR-0013: Containers, cloud-neutral; cloud choice at M7
- Status: Proposed · Date: 2026-10-18
## Context
Develop on the owner's PC; later AWS or Google Cloud including their managed database.
## Decision
Everything runs as containers configured by environment variables; no cloud-specific SDK outside adapters (storage, secrets). At M7 we write a short comparison (cost, managed Postgres + pgvector, container hosting, India region, ops effort) and pick AWS (e.g. ECS Fargate + RDS + S3) or Google Cloud (Cloud Run + Cloud SQL + GCS); infrastructure as code with Terraform.
## Consequences
+ Moving to cloud is configuration, not rewrite. − We avoid cloud-only conveniences until M7.
