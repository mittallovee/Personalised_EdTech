# 03 — Recommended Approach (How a Big-Tech Team Would Do This)

> Status: **Proposal** — recommendations marked *(pending Qn)* depend on answers in
> [`04-open-questions.md`](./04-open-questions.md).

## 1. The way companies like Google/Microsoft work

They don't start by coding, and they don't write one giant spec either. They layer documents, and each
layer answers a different question:

| Layer | Document type | Answers | Who reviews |
|---|---|---|---|
| Why / what | **Vision & strategy**, **PRD** (Product Requirements Doc) per product/feature | What problem, for whom, what success looks like, scope & non-goals | Product + business |
| Behaviour | **User journeys**, **user stories + acceptance criteria**, wireframes | What exactly the user does and sees | Product + design + eng |
| Language | **Domain glossary** ("ubiquitous language"), **context map** | What each word means, which module owns it | Everyone |
| How (system) | **Design Docs** (Google style), **C4 architecture diagrams**, **NFR/SLO doc** | How we'll build it, alternatives considered, trade-offs | Senior engineers |
| Contracts | **OpenAPI spec**, **event schemas**, **data model (ERD)** | Exact interfaces between parts | Eng + client teams |
| Safety | **Threat model**, **Privacy Impact Assessment** | What can go wrong, how we defend | Security/privacy |
| Decisions | **ADRs** (Architecture Decision Records) | Why we chose X over Y (permanent log) | Eng |
| Running it | **Runbooks**, **SLO dashboards**, **incident & post-mortem process** | How to operate and recover | Eng/ops |

Rules they follow:
- **Docs-as-code**: docs live in Git next to the code, reviewed via pull requests, versioned.
- **A design doc is approved before major code is written.** It must list *goals*, *non-goals* and
  *alternatives considered*.
- **Every significant decision becomes an ADR**, so future engineers know *why*.
- **Contracts before implementation**: API and event schemas are agreed first; frontend and backend then
  work in parallel against the contract (using mock servers).

## 2. Target documentation structure (spec-v1)

```text
docs/
  README.md                      index + reading order
  product/
    vision-and-strategy.md       whole platform, not just question bank
    personas.md                  faculty, reviewer, student, parent, admin, partner
    journeys/                    end-to-end journeys (one file each)
    prd/                         one PRD per product area
      prd-content-studio.md        (question bank, ingestion, review)
      prd-ai-assist.md
      prd-test-builder.md
      prd-exam-delivery.md         NEW — live exam engine
      prd-student-practice.md      NEW
      prd-results-analytics.md     NEW
      prd-org-admin.md             NEW — centres, batches, enrollments
  domain/
    glossary.md                  single source of truth for terms
    context-map.md               bounded contexts + ownership
    question-model.md            content blocks + answer schemas per type (JSON Schema)
    state-machines.md
  architecture/
    c4-context.md / c4-containers.md
    nfr-and-slos.md              numbers: scale, latency, uptime, RPO/RTO, cost
    api-style-guide.md
    data-model.md                ERD per module
    security-threat-model.md
    privacy-dpdp.md
    adr/                         0001-modular-monolith.md, 0002-..., one decision per file
  api/
    openapi.yaml                 the contract
    events/                      event schemas (AsyncAPI or JSON Schema)
  engineering/
    standards.md  repo-structure.md  testing-strategy.md  ci-cd.md
    release-and-rollback.md  ai-assisted-development.md
  operations/
    runbooks/  incident-process.md  backup-restore.md
  delivery/
    roadmap.md  milestones.md  backlog.md  risk-register.md
  spec-v0/                       the original pack (kept for history)
```

## 3. Architecture direction

### 3.1 Platform shape: one core backend, many clients

```text
 Clients            Content Studio (web)   Admin console   Student app (Android/iOS/web)   Exam client   Partner systems
                          │                     │                     │                         │              │
 Edge                     └──────────── API Gateway / Load balancer, WAF, rate limiting, auth check ───────────┘
                                                              │
 Core backend     ┌───────────────────────── Modular monolith (one deployable, strict modules) ───────────────────────┐
 (/api/v1)        │ Identity&Access │ Org&Enrollment │ Taxonomy │ Content(Question Bank) │ Ingestion │ Review │       │
                  │ AI Orchestrator │ Search │ Media │ Assessment Authoring (Test Builder) │ Notifications │ Audit  │       │
                  └───────────────────────────────────────────────────────────────────────────────────────────────────┘
 Separately       ┌── Exam Delivery service (extract early: different scaling — spiky, write-heavy, must not go down) ──┐
 scaled           ┌── Workers: document extraction (Python), AI jobs, embeddings, exports, scoring ─────────────────────┐
 Data             PostgreSQL (+ read replica)   Redis (cache, rate limits, exam sessions)   S3 (files)   Queue
 Later            Event stream → Data warehouse → Analytics & Recommendations
```

Key points:
- **Keep the modular monolith** (ADR-001 is correct) **but** put the API in its **own backend service**,
  not inside the Next.js web app. That way every client (web, mobile, exam, partners) calls the same API.
- **Plan the Exam Delivery engine as a separate service from the start.** It has a completely different
  load pattern and risk profile. Everything else stays in the monolith until measurements say otherwise.
- **Contract-first API** (OpenAPI) → generated SDKs for TypeScript/Kotlin/Swift clients.
- **API surfaces with different stability**: `studio`/`admin` (internal, can change faster) vs.
  `learner`/`exam`/`partner` (external, versioned, with a deprecation policy).
- **Design for the student layer now, build it later**: identity model, tenancy hierarchy, test-version
  snapshot and the rendering contract must already allow it, even if the student app ships in a later phase.

### 3.2 Proposed tech stack *(pending Q9–Q11)*

Optimised for a small team, readability and hiring in India. Each line becomes an ADR.

| Concern | Recommendation | Why | Alternatives |
|---|---|---|---|
| Language | **TypeScript** end-to-end (+ **Python** for document extraction workers) | One language for most code; Python has the best PDF/OCR tooling | Java/Kotlin (Spring) or Go for the backend |
| Repo | **Monorepo** (pnpm workspaces + Turborepo or Nx) | Shared types/SDK, one CI, atomic changes | Polyrepo |
| Backend framework | **NestJS** (modules, dependency injection, guards) | Imposes a consistent structure humans can navigate | Fastify + hand-rolled structure |
| API contract | **OpenAPI 3.1** + generated clients | Contract is reviewable; clients can't drift | GraphQL (later, if needed by apps) |
| Database | **PostgreSQL 16+** (managed: AWS RDS/Aurora), **pg_trgm** + **pgvector** | One DB for relational, search and embeddings at MVP | OpenSearch later for heavy faceted search |
| DB access & migrations | **Drizzle** or **Prisma** + reviewed SQL migrations | Type-safe queries, migrations in Git | Kysely, Flyway |
| Queue / jobs | **BullMQ on Redis** (or **pg-boss** if avoiding Redis early) | Retries, backoff, DLQ, priorities; Redis also needed for exam engine | AWS SQS |
| Identity | **Use a proven IdP / auth library** (Keycloak/Zitadel self-hosted, or Auth0/Cognito/Clerk), OIDC + OAuth2 | Never hand-roll auth; supports SSO, OTP, M2M clients | Better Auth (library) |
| Web apps | **Next.js + React + TypeScript**, component library (shadcn/ui or MUI), TanStack Query | Mainstream, strong ecosystem | — |
| Mobile | **React Native (Expo)** *(pending Q4)* | Share TypeScript, SDK and rendering logic | Native Kotlin/Swift, Flutter |
| Maths rendering | **KaTeX** with one shared renderer package | Fast, consistent across clients | MathJax |
| Document extraction | Evaluate **buy** (Mathpix) vs **open source** (Docling/Marker/PyMuPDF) on a golden set | Extraction quality decides ingestion success | — |
| AI gateway | **LiteLLM** (as spec) | Multi-provider, budgets, logging | Portkey, own gateway |
| Cloud | **AWS ap-south-1 (Mumbai)** *(pending Q10)* | Data residency, latency for Indian users | GCP/Azure India regions |
| Compute | **ECS Fargate** containers to start | No server patching, simpler than Kubernetes, more robust than hand-managed EC2 | EC2 (spec), EKS later |
| IaC | **Terraform** | As spec | Pulumi |
| Observability | **OpenTelemetry** → Grafana stack (or Datadog), **Sentry** for errors | Vendor-neutral traces/metrics/logs | — |
| Feature flags | **OpenFeature** + Unleash/GrowthBook | Safe releases | — |
| CI/CD | **GitHub Actions** | Repo is on GitHub | — |

### 3.3 Guardrails that stop "vibe-coded" decay

Rules **enforced by tools**, not by memory:
1. **Contract-first**: an API change starts as an OpenAPI diff in a PR; CI fails on breaking changes
   (e.g. `oasdiff`) unless the version is bumped.
2. **Module boundaries enforced**: `dependency-cruiser` / Nx module-boundary lint. One module cannot
   import another module's internals or tables, only its public interface.
3. **Domain rules as pure, tested code**: state machines, permission rules, answer validation, scoring —
   unit-tested with near-100% coverage. These are the parts that must never break.
4. **Strict TypeScript, ESLint, Prettier**, pre-commit hooks, **no `any`** in domain code.
5. **Branch protection**: PR required, green CI required, at least one human reviewer, **CODEOWNERS** per module.
6. **Small PRs** (aim < 400 changed lines), conventional commits, PR template with checklist (security,
   tenant isolation, migration safety, tests, observability, docs).
7. **Migrations** reviewed like code; expand/contract only; automated check for destructive SQL.
8. **Tenant-isolation tests** run on every PR (attempt cross-tenant reads/writes, expect denial).
9. **Observability from day one**: request IDs, structured logs, traces. If you can't see it, you can't run it.
10. **ADRs** for every significant choice; **Definition of Done** includes docs updated.
11. **AI-assisted coding policy**: AI works from an approved spec/story, writes tests first or alongside,
    follows `AGENTS.md`/`CLAUDE.md` conventions in the repo, and **a human reviews and understands every PR** before merge.

## 4. Recommended path from here

| Step | Output | Gate |
|---|---|---|
| **0. Discovery** (now) | Answers to [open questions](./04-open-questions.md) | You review |
| **1. Product layer** | Vision v2, personas, top 8–10 user journeys, PRD list, MVP scope + non-goals | You sign off scope |
| **2. Domain layer** | Glossary v1, context map, question model with JSON Schemas, state machines v2 (fixing I-1…I-11) | Domain frozen for MVP |
| **3. Architecture layer** | NFR/SLO numbers, C4 diagrams, ADRs 001–015, API style guide, OpenAPI v0 for MVP, ERD, threat model, DPDP note | Design review |
| **4. Engineering layer** | Repo scaffold, standards, CI pipeline, `AGENTS.md`, testing strategy | "Walking skeleton" deploys to staging |
| **5. Build in vertical slices** | Slice 1: login + org + question CRUD → Slice 2: versioning/review/audit → Slice 3: ingestion … (as doc 32) | Each slice: deployed, tested, demoed |

**Walking skeleton** = the thinnest end-to-end version that touches every layer (login → API → DB →
deployed on staging with CI, logs and monitoring) before any feature depth is added. It shows early whether
the architecture holds up end to end.

Suggested MVP boundary *(pending Q1, Q4)*: Content Studio (manual creation → review → publish → search)
+ ingestion + Test Builder, **with the API, identity and data model already designed for** students and
exams. Exam delivery is the next major release, not an afterthought.
