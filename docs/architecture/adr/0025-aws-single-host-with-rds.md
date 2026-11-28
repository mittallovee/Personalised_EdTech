# ADR-0025: Host on AWS, cost first: one small server for the containers, RDS for the database, S3 for files
- Status: **Proposed** (owner chose AWS and "cost effective, no high availability now" on 2026-11-28; the details below await approval) · Date: 2026-11-28
- Supersedes the cloud choice left open in [ADR-0013](./0013-cloud-neutral-deployment.md); comparison in [m7-cloud-comparison.md](../m7-cloud-comparison.md)

## Context
The owner chose AWS, with about US$100 of new-account credits, no requirement to keep data in India, and a wish to save cost:
high availability (a standby copy for fast recovery) can come later, and cheaper services are preferred. The first comparison
assumed ECS Fargate, a load balancer and a NAT gateway (about US$300 to 410 a month), which would use up US$100 of credits in
about a month. That is too much for one coaching's first months.

## Decision
- **One EC2 server** (ARM, `t4g.medium`: 2 vCPU, 4 GB) runs the same `compose.yaml` containers as on the owner's PC: web, api,
  worker and the **ingest-worker sandbox exactly as ADR-0024 specifies** (internal-only Docker network, read-only filesystem,
  `cap_drop: ALL`, limits). This keeps the sandbox guarantees intact and costs far less than Fargate.
- **No load balancer, no NAT gateway.** The server has one public address. A small reverse proxy (Caddy) on it serves HTTPS with
  an automatic certificate. The security group allows only ports 80 and 443 from anywhere; there is **no SSH**: the owner and
  Claude reach the server through AWS Systems Manager Session Manager (a browser shell with no open port).
- **Database: Amazon RDS for PostgreSQL 17, `db.t4g.micro`, single zone**, in private subnets, reachable only from the server's
  security group. Automated backups (point-in-time recovery) kept 7 days. The daily restic copy to Cloudflare R2 (ADR-0021)
  stays as an independent second copy. A bigger size and a standby copy are one Terraform variable each, later.
- **Files: an S3 bucket** (private, encrypted, versioned, public access blocked) through a new `Storage` adapter (planned in
  ADR-0012). The server's role may read and write only that bucket; nothing in a key reaches the browser except through the API.
- **Secrets:** AWS Systems Manager Parameter Store (free for standard parameters), read by the server's role at start-up.
- **Monitoring:** CloudWatch logs and basic alarms (billing, CPU, disk, database storage, "site down" check). The self-hosted
  Grafana stack is **not** run in the cloud.
- **Infrastructure as code:** Terraform in `infra/aws/`, with the region as a variable. The owner runs `terraform apply` from
  **AWS CloudShell** (a free browser terminal already signed in to the account); Claude writes and explains the plan but is
  **not given the account's keys**.
- **Region:** the owner said location does not matter, so cost decides. `us-east-1` is cheapest; **Mumbai (`ap-south-1`) costs
  about US$7 more a month at this size and answers about ten times faster for faculty in India.** Proposed default: Mumbai,
  unless the owner says otherwise before the first apply (changing it later means moving the database).
- **Safety on a small budget:** an AWS Budget with email alerts at 50%, 80% and 100% of a monthly limit, created before anything
  else; MFA on the root user; root not used for daily work.

## Rough monthly cost (my estimate, not a quote; confirm in the AWS Pricing Calculator)
| Item | US$ |
|---|---|
| EC2 `t4g.medium` + 30 GB disk | 28 to 35 |
| RDS `db.t4g.micro` + 20 GB | 14 to 18 |
| Public IPv4 address | about 4 |
| S3, CloudWatch, Parameter Store, data out | 3 to 10 |
| **Total** | **about 50 to 65** |

So US$100 of credits lasts **roughly 1.5 to 2 months**, then the account pays about this much. (As I understand AWS's current
new-account "free plan", credits last up to six months and the account must be moved to a paid plan before then or it is closed;
confirm this on the sign-up screen.)

## Consequences
+ Cheapest sensible way to have managed Postgres, off-machine files, backups and the exact sandbox of ADR-0024.
+ Same containers locally and in the cloud; Terraform is small enough for one person to read.
− **One server is a single point of failure.** If it dies, the site is down until it is rebuilt (Terraform plus the compose
  file: expected under an hour, and no data is lost because data lives in RDS and S3). Accepted for now; high availability is a
  later, larger-cost step (two servers behind a load balancer, RDS standby).
− We patch the server's operating system and Docker ourselves (a scheduled automatic-update setting; reviewed monthly).
− `db.t4g.micro` has 1 GB of memory: fine for the first coaching, to be re-measured with the k6 load tests (K-08) on staging
  before real use grows.
− RDS does not give a true superuser, so the backup script's "bypass row-level security" rule needs the one-afternoon check in
  the comparison (section 4) before the first restore drill.
## Alternatives considered
- ECS Fargate + ALB + NAT + RDS: about US$300 to 410 a month; right for later growth, wrong for now.
- Everything on one server including PostgreSQL in a container: about US$15 a month cheaper, but not "managed PostgreSQL" (M7
  exit criterion) and a disk failure would lose the live database between daily copies.
- Google Cloud Run + Cloud SQL: see the comparison; weaker fit for the sandbox and the always-on worker.
