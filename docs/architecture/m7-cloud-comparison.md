# M7: AWS or Google Cloud? A short comparison

> Status: **Draft for the owner's decision** · 2026-11-28 · Follows [ADR-0013](./adr/0013-cloud-neutral-deployment.md)
> (cloud-neutral containers, choose at M7) · Phase plan: M7 "Hardening & cloud".
> **Update 2026-11-28: the owner chose AWS, with about US$100 of credits and a wish to save cost. The cost-first design is in
> [ADR-0025](./adr/0025-aws-single-host-with-rds.md) (one EC2 server + RDS + S3, about US$50 to 65 a month); the Fargate figures
> below are the "growth" option, not the plan.**
>
> Once you choose, this becomes ADR-0025 and I write the Terraform (infrastructure as code: the cloud set-up kept as
> reviewed text files, so it can be rebuilt and nothing is clicked together by hand).
>
> **Cost numbers below are my rough planning estimates from public list prices as I remember them, not quotes.**
> Check them in each provider's price calculator before relying on them. Everything else is from this repository.

## 1. What we have to host

From `compose.yaml` and the ADRs, the app is five kinds of running thing plus data:

| Piece | What it needs from the cloud |
|---|---|
| **web** (Next.js) and **api** (FastAPI) | Ordinary container hosting, HTTPS, health checks, scale on load |
| **worker** | A container that runs **all the time** and polls the database for jobs (ADR-0007). It does not wait for web requests, so "scale to zero" hosting does not suit it |
| **ingest-worker** (the sandbox, ADR-0024) | The hardest fit. It opens untrusted documents, so it must run with **no internet, a read-only filesystem, all Linux capabilities dropped, 1 GB memory, 1 CPU, and a database login that reaches only the upload tables** |
| **PostgreSQL 17** | Managed. We use row-level security with forced policies on every tenant table (tenant isolation), `pg_trgm` (typo-tolerant search), `FOR UPDATE SKIP LOCKED` (job claiming), advisory locks, and several database roles |
| **File storage** | Today a Docker volume shared by api, worker and ingest-worker (`LocalDiskStorage`). The cloud needs an **S3/GCS adapter that does not exist yet** (ADR-0012 planned it; `presign` was deferred to it) |
| **Observability** | Today a self-hosted OpenTelemetry collector, Tempo, Loki, Prometheus and Grafana. In the cloud we would send to the provider's own monitoring instead of running five more services |
| **Backups** | Daily restic to Cloudflare R2 already works (ADR-0021). A managed database adds point-in-time recovery |

Requirements that decide the choice: data in **India** (DPDP Act, N-12; and your question Q10 in
[open questions](../review/04-open-questions.md)), a **restore drill** and a **restore tested** (M7 exit criterion),
**monitoring and alerts** (K-13), **staging rehearsal of migrations** (K-19), and a small bill that one person can understand.

## 2. Side by side

| | **AWS** (ECS Fargate + RDS + S3) | **Google Cloud** (Cloud Run + Cloud SQL + Cloud Storage) |
|---|---|---|
| **India regions** | Mumbai (`ap-south-1`) and Hyderabad (`ap-south-2`) | Mumbai (`asia-south1`) and Delhi (`asia-south2`) |
| **Managed Postgres** | RDS for PostgreSQL 17, Multi-AZ optional, point-in-time recovery, `pg_trgm` supported | Cloud SQL for PostgreSQL 17, HA optional, point-in-time recovery, `pg_trgm` supported |
| **web, api** | Fargate services behind an Application Load Balancer | Cloud Run services (HTTPS built in, no load balancer to buy) |
| **worker** (always on, polling) | A Fargate service, the natural fit | Cloud Run can do it only with "CPU always allocated" and a minimum of one instance, which stops it being cheap; it is a service pretending to be a worker |
| **ingest-worker sandbox** | Fargate can express **almost every** rule of ADR-0024: read-only root filesystem, dropped capabilities, memory and CPU limits, a security group that allows traffic only to the database and the storage endpoint. A free **S3 gateway endpoint** means it can reach storage with no internet at all | Cloud Run cannot set "read-only root filesystem" or "drop capabilities" as we do in compose (it runs in Google's own sandbox instead, which is strong but different). A no-internet rule needs a VPC with egress firewall rules. The exact guarantees of ADR-0024 would have to be re-argued; GKE Autopilot could match them but is much more to operate |
| **Reaching AI providers** (internet) | Private subnets need a **NAT gateway** (a fixed monthly charge) | Cloud Run reaches the internet by default; no NAT unless we force all traffic through a VPC |
| **Shared files for 3 services** | S3 via the adapter; no shared disk | Cloud Storage via the adapter; no shared disk |
| **Secrets** (AI master key, DB passwords) | Secrets Manager (injected as environment variables) | Secret Manager (same) |
| **Monitoring** | CloudWatch logs and metrics; OpenTelemetry traces supported | Cloud Logging, Monitoring and Trace; OpenTelemetry supported |
| **Deploy from GitHub Actions** | OIDC (short-lived credentials, no stored keys) | Workload Identity Federation (same idea) |
| **Terraform** | Mature, the most examples | Mature, good |
| **Console and learning curve for one person** | Wider and more fiddly (IAM, VPC, subnets, security groups) | Narrower; Cloud Run is the easiest part of either |
| **Pricing for this size** | Fixed charges add up: load balancer, NAT gateway, always-on tasks | Cheaper web and api when idle; the always-on worker and the database cost the same |

## 3. Rough monthly cost (small production, one region, no high availability)

These are order-of-magnitude figures for **one coaching's worth of traffic**, in US dollars:

| Item | AWS | Google Cloud |
|---|---|---|
| Database (2 vCPU, 8 GB, 100 GB disk) | about 130 to 180 | about 130 to 180 |
| web + api + worker + ingest-worker (about 2.5 vCPU, 5 GB in total, always on) | about 90 to 110 | about 90 to 130 |
| Load balancer and NAT gateway | about 60 to 80 | about 0 to 10 |
| Storage, logs, secrets, backups | about 20 to 40 | about 20 to 40 |
| **Total** | **about 300 to 410** | **about 240 to 360** |

Turning on database high availability (a second copy in another zone, for faster recovery) roughly **doubles the database line**
on either cloud. The database dominates the bill on both, so **cost is not a strong reason to prefer one**. AI usage is separate
and paid by each coaching to its provider (ADR-0023); neither cloud's own AI services (Bedrock, Vertex AI) change this design.

## 4. Risks that apply to both (a day-one spike, before committing)

I would spend one afternoon on a throwaway instance of the chosen cloud and prove these, because they are where managed
databases most often differ from the plain PostgreSQL we test against:

1. **Row-level security bypass for backups.** `backup-db.sh` refuses a role that cannot bypass row-level security. Managed
   databases do not give a true superuser, so we must confirm which role can bypass it (or use the provider's own snapshots
   for the full copy). **This is the thing most likely to surprise us.**
2. **Roles.** `ensure-app-role.sh` creates `qbank_app`, `qbank_worker` and `qbank_ingest` with `NOBYPASSRLS`; confirm the
   admin user may create them and grant columns the way migrations 0043 to 0047 do.
3. **Connection pooling.** If a pooler is used, transaction-level pooling must keep working with `set_config(..., true)` tenant
   settings and advisory locks (both are transaction-scoped, so they should).
4. **Storage adapter and the sandbox.** Build the S3/GCS `Storage` class and prove the ingest worker reads an original and
   writes page pictures with **no internet route**.
5. **A real restore** into a fresh instance from both the provider's point-in-time recovery and our restic copy, timed against
   the targets in [ADR-0017](./adr/0017-backups-and-restore.md) (K-03, K-16, M7 exit criterion).

## 5. Recommendation

**AWS with ECS Fargate, RDS and S3, in Mumbai, with Hyderabad as the disaster-recovery region.**

Why, in the order that mattered:

1. **The sandbox.** ADR-0024 is a hard security decision (K-17). Fargate lets us keep it nearly word for word (read-only
   filesystem, dropped capabilities, limits, no internet, an S3 endpoint inside the private network). On Cloud Run we would have
   to weaken or re-argue those rules.
2. **The always-on worker.** ECS runs the same containers as `compose.yaml` with the same commands; the move to the cloud really
   is "configuration, not rewrite" (ADR-0013). Cloud Run is built for request-driven containers.
3. **Same shape locally and in the cloud**, so what we test on your PC is what runs.

What AWS costs us: about US$50 to 70 a month more in fixed charges (load balancer, NAT gateway), and a steeper learning
curve for you (networks and permissions). The Terraform I write hides most of that, and you would read plans, not click consoles.

**Choose Google Cloud instead if** you already have an account or credits there, a colleague who runs it, or you decide the
sandbox can run with Google's own isolation (Cloud Run) rather than the exact compose rules. That is a legitimate choice with a
slightly lower bill and simpler web hosting; the cost is re-opening ADR-0024's guarantees and running the worker less naturally.

## 6. What I need from you

1. **Which cloud?** Do you or your organisation already have an AWS or Google Cloud account, credits or a preference?
   (If yes, that probably outweighs section 5.)
2. **Must all data stay in India?** I have assumed yes (Mumbai primary, Hyderabad or Delhi for recovery).
3. **Monthly infrastructure budget** (excluding AI), and **do you want database high availability now** or after real use starts?
4. **Service targets for K-13** (for example 99.5% monthly uptime; recovery within 4 hours; at most 15 minutes of data lost).
   Point-in-time recovery gets us to minutes of data loss; the daily restic copy stays as an independent second copy in another provider.
5. **You create the account and a billing alarm** (I cannot create accounts, pay, or pick hosting for you). Then I write the
   Terraform in `infra/`, the storage adapter, the spike above, and the staging rehearsal (K-19).

## 7. Work plan once chosen (each a small pull request)

| PR | What | Needs you |
|---|---|---|
| 7a | ADR-0025 (the choice), the day-one spike notes (section 4) | The account |
| 7b | `Storage` adapter for S3 (or GCS) with tests; `presign` | |
| 7c | Terraform: network, database, storage, secrets, container services (staging first) | Review the plan output |
| 7d | CI deploy with short-lived credentials; staging rehearsal of migrations (K-19) | |
| 7e | Monitoring and alerts to the provider's tools; service targets (K-13) | Agree targets |
| 7f | Real restore drill from both copies; performance pass (K-08 numbers on staging); security checklist | Witness the restore |
| 7g | Production, owner sign-off | Sign-off |
