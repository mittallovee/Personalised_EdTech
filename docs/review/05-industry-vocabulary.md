# 05 — Industry Vocabulary & the Questions Professionals Ask

> A learning guide for the product owner. Each term: **what it means** → *how it applies to this project*.

## 1. "What you want" → the industry word for it

| What you said | Industry term |
|---|---|
| "Backend that many apps can call" | **API-first platform**, **headless backend**, **multi-client API** |
| "Student app, faculty app, exam app" | **Client applications** / **frontends** / **API consumers** |
| "Code humans can understand and manage" | **Maintainability**, **readability**, **clean architecture**, **separation of concerns** |
| "Not vibe-coded, won't break in future" | **Engineering rigour**, **quality gates**, **regression prevention**, **technical-debt control** |
| "Like Google/Microsoft make" | **Production-grade**, **enterprise-grade**, **industry best practices** |
| "Prepare all docs first" | **Requirements engineering**, **design phase**, **design docs**, **specification** |
| "Can scale" | **Scalability** (horizontal/vertical), **elasticity**, **capacity planning** |
| "Many institutes use the same software" | **Multi-tenant SaaS** |
| "Complete flow and logic" | **User journeys**, **business processes**, **domain model**, **state machines** |

## 2. Product & planning

- **PRD (Product Requirements Document)** — what we're building and why, for whom, success metrics, scope, **non-goals**.
- **MVP (Minimum Viable Product)** — smallest version that delivers real value to real users.
- **Persona** — a typical user type (e.g. "Physics reviewer at a Kota centre").
- **User journey** — the full path a persona takes to reach a goal (e.g. upload PDF → published questions).
- **User story** — "As a *reviewer*, I want *X* so that *Y*", plus **acceptance criteria** (testable conditions).
- **Epic** — a large group of related stories.
- **Backlog** — prioritized list of work. **P0/P1/P2** = priority levels.
- **Roadmap / milestone / release** — when things ship.
- **Definition of Ready / Done (DoR/DoD)** — checklist before work starts / before it counts as finished.
- **Scope creep** — requirements keep growing without an explicit decision.
- **Vertical slice** — a feature delivered through all layers (UI → API → DB) instead of building one layer at a time.

## 3. Architecture

- **Monolith / Modular monolith / Microservices** — one deployable app / one app with strict internal modules / many small separately-deployed services. *We start modular monolith; extract the exam engine early.*
- **Bounded context** (from **DDD — Domain-Driven Design**) — a module with its own model and vocabulary (e.g. "Content", "Exam Delivery").
- **Ubiquitous language** — everyone (business + code) uses the same words with the same meaning (Master, Variant, Version).
- **C4 model** — standard set of architecture diagrams: Context → Containers → Components → Code.
- **ADR (Architecture Decision Record)** — a short file recording one decision, its options and why it was chosen.
- **Design doc / RFC** — a proposal reviewed before building something significant.
- **NFR (Non-Functional Requirement)** — quality requirements: performance, security, availability, cost.
- **Single source of truth (SSOT)** — only one place owns a piece of data.
- **Coupling / cohesion** — how dependent modules are on each other (want low) / how related things inside a module are (want high).
- **Event-driven** — modules react to events ("QuestionPublished") instead of calling each other directly.
- **Outbox pattern** — save the event in the same DB transaction as the change, publish it afterwards, so events are never lost.
- **CQRS** — separate models for writing and reading (useful for exam results and analytics later).
- **BFF (Backend for Frontend)** — a thin backend tailored to one client (e.g. mobile) sitting in front of the core API.
- **Build vs. buy** — write it ourselves or use an existing product/service.

## 4. API

- **API contract** — the precise agreement of requests/responses. **OpenAPI** is the standard format for REST contracts.
- **Contract-first / API-first** — design and review the contract before writing code.
- **SDK** — a ready-made library (generated from OpenAPI) that apps use to call the API.
- **REST / GraphQL / gRPC** — API styles. *REST for us; GraphQL optional later.*
- **Versioning** (`/api/v1`) and **deprecation policy** — how old clients keep working when the API changes.
- **Breaking change** — a change that makes existing clients fail. Must never happen silently.
- **Idempotency** — calling the same request twice has the same effect as once. *Critical for exam answer saves and payments.*
- **Pagination (cursor-based)** — returning large lists in pages using a pointer, not page numbers.
- **Rate limiting / throttling** — capping requests per client to protect the system.
- **Webhook** — your system calls a partner's URL when something happens.
- **Long-running operation** — request returns a job ID immediately; client checks status later (ingestion, AI jobs).
- **API gateway** — front door that handles auth, rate limits and routing for all APIs.

## 5. Identity & security

- **Authentication (AuthN)** — who are you? **Authorization (AuthZ)** — what may you do?
- **OAuth 2.0 / OIDC (OpenID Connect)** — standard protocols for login and access tokens. **SSO** — single sign-on.
- **JWT** — a signed token carrying identity claims. **Session** — server-stored login state.
- **IdP (Identity Provider)** — system that manages logins (Keycloak, Auth0, Cognito…).
- **RBAC / ABAC** — permissions by role / by attributes (e.g. "reviewer of Physics at Centre X").
- **Least privilege** — give only the minimum access needed.
- **Tenant isolation** — one institute can never see another's data. **IDOR** — a bug where changing an ID in the URL shows someone else's data.
- **OWASP Top 10** — the standard list of most common web security risks.
- **Threat model (STRIDE)** — structured way to list what attackers could do.
- **Encryption in transit / at rest** — TLS on the network / encrypted disks and backups.
- **Secrets management** — API keys and passwords stored in a vault, never in code.
- **PII** — personally identifiable information. **DPDP Act** — India's data protection law (consent, minors, breach reporting).

## 6. Data

- **Schema** — structure of the data. **ERD** — diagram of tables and relationships.
- **Migration** — a versioned script changing the DB schema. **Expand/contract** — add new structure first, remove old later, so nothing breaks.
- **Transaction / ACID** — a group of changes that all succeed or all fail.
- **Index** — makes lookups fast. **Full-text search**, **trigram (fuzzy) search**, **embeddings / vector search** (meaning-based).
- **Immutability / append-only** — never edit, only add new versions.
- **Audit trail** — who did what, when.
- **Read replica** — copy of the DB for read traffic. **Sharding/partitioning** — splitting big tables.
- **Cache** (Redis) / **CDN** — keep frequently read data close and fast.
- **Data warehouse** — separate store for analytics (doesn't slow the main DB).
- **Soft delete** — mark as deleted instead of removing.

## 7. Reliability & operations

- **SLI / SLO / SLA** — what we measure (latency) / our internal target (p95 < 300 ms, 99.9% uptime) / promise in a contract.
- **p95 / p99 latency** — 95%/99% of requests are faster than this.
- **Availability "nines"** — 99.9% ≈ 8.8 h downtime/year; 99.99% ≈ 53 min/year.
- **RPO / RTO** — max data loss acceptable / max time to recover after a disaster.
- **Observability** — **logs**, **metrics**, **traces** (**OpenTelemetry** is the standard).
- **Alerting / on-call / runbook** — notify a human / who responds / step-by-step fix guide.
- **Incident / post-mortem (blameless)** — an outage / the write-up of causes and fixes without blaming people.
- **Horizontal scaling** — add more machines. **Autoscaling** — automatically.
- **Queue / worker / DLQ (dead-letter queue)** — background job system / job processor / where failed jobs go.
- **Retry with exponential backoff** — wait longer between each retry.
- **Load test / stress test / spike test** — simulate many users / beyond limits / a sudden surge (*the 10:00 AM exam start*).
- **Graceful degradation** — if AI is down, the rest still works.

## 8. Engineering process & quality

- **Git, branch, PR (pull request), code review, merge**.
- **Trunk-based development** — short-lived branches merged to main often.
- **CI/CD** — automatic build+test on every change / automatic deployment.
- **Quality gates** — checks that must pass before merge (lint, typecheck, tests, security scan).
- **Linting / formatting / static typing** — automatic style and bug checks.
- **Unit / integration / contract / E2E tests** — test small functions / modules with DB / API agreements / whole user flows.
- **Test coverage** — % of code exercised by tests (useful signal, not a goal by itself).
- **Regression** — something that used to work breaks.
- **Feature flag** — turn a feature on/off without redeploying.
- **Canary / blue-green deployment / rollback** — release to a few users first / switch between two environments / undo a release.
- **IaC (Infrastructure as Code)** — servers defined in files (Terraform), not clicked manually.
- **Environments** — local, dev, staging (copy of prod), production.
- **Technical debt** — shortcuts that cost more later.
- **CODEOWNERS** — file declaring who must review changes to which folder.
- **Monorepo** — all apps and packages in one repository.

## 9. EdTech-specific terms

- **Item bank** — psychometrics term for question bank; **item** = question.
- **CBT (Computer-Based Test)** — exam taken on a computer (JEE Main style).
- **Blueprint / test specification** — rules for how many questions of which topic/difficulty.
- **Marking scheme** — +4/−1, partial marking, etc.
- **IRT (Item Response Theory)** — statistical method to measure true question difficulty from student responses.
- **Adaptive testing (CAT)** — next question chosen based on previous answers.
- **Normalization / percentile** — making scores comparable across exam shifts.
- **Proctoring** — supervising online exams (camera, screen, lockdown browser).
- **QTI 3.0** (IMS Global / 1EdTech) — standard format to exchange questions and tests between systems.
- **LTI 1.3** — standard to plug your tool into another LMS (Moodle, Canvas).
- **xAPI / Caliper** — standards for recording learning activity events.
- **LMS** — learning management system.

## 10. Questions professionals ask (use these in every design discussion)

**About requirements**
- What problem does this solve, for whom? What is explicitly *out of scope* (non-goal)?
- How will we know it worked (success metric)?
- What are the acceptance criteria?

**About scale and performance**
- How many users / records / requests per second — today, and in 3 years? What is the **peak**?
- What latency is acceptable (p95)?
- What happens at 10× the load?

**About failure**
- What happens if this component fails? What is the **blast radius**?
- Is this operation **idempotent**? What if it's retried?
- How do we **roll back** a bad release or a bad migration?
- What's our RPO/RTO?

**About data and security**
- Who owns this data, and who can see it? How is **tenant isolation** guaranteed and tested?
- Is there any **PII**, data from minors, or regulated data? Where is it stored, for how long?
- What's the worst thing an attacker could do here?

**About design quality**
- Which module owns this? Is there one **source of truth**?
- What alternatives did we consider and why reject them? (Is there an ADR?)
- Does this introduce a **breaking change** to the API?
- How will we **observe** it in production (logs/metrics/alerts)?
- How is it tested? Can a new engineer understand it in a day?

**About cost and vendors**
- Build or buy? What's the monthly cost at expected scale? What's the lock-in risk?
