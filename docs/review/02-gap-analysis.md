# 02 — Gap Analysis of spec-v0

> Status: **Review draft**. Severity: 🔴 must resolve before design/coding · 🟠 resolve before that module is built · 🟢 nice to have.

## 1. Verdict

spec-v0 is a **good skeleton**: the core domain thinking (Master/Variant/Version, immutability, ingestion
staging, AI provenance, modular monolith, outbox, state machines, ADRs) matches what a mature engineering
team would choose.

It is **not yet buildable as an industry-grade platform**, for three reasons:

1. **Scope gap.** It specifies the *authoring* product (faculty question bank). Your stated goal is a
   *platform* whose backend serves many apps — student app, faculty app, live-exam app. The delivery side
   (students, exams, results, analytics) is ~1 page.
2. **Depth gap.** Each document is 1–5 KB of bullet points. Many statements are still undecided
   ("session/JWT as selected by implementation", "Redis/Postgres/SQS", "optional RLS", "where practical").
   A buildable spec makes these decisions and records them (ADRs).
3. **No numbers.** There are no scale targets, latency/uptime objectives (SLOs), budgets, or retention periods.
   Architecture choices can't be justified without them.

---

## 2. Internal inconsistencies found (fix in spec-v1)

| # | Sev | Issue | Where |
|---|---|---|---|
| I-1 | 🔴 | **Who approves?** Doc 03/09 say an *Approver* approves; the transition table in doc 27 says *Reviewer/Validator* moves IN_REVIEW → APPROVED. Is it 2 stages (review, then approve) or 1? | 03, 09, 27 |
| I-2 | 🔴 | **Answer is stored per language.** `question_versions` has `answer` and `language_code` together, so English v2 could say "B" while Hindi v1 says "C". The answer, type, option keys, assets and taxonomy are language-independent and should live in a language-neutral layer, with only text localized. | 05, 06 |
| I-3 | 🔴 | **Translation staleness.** When English v3 fixes an answer, nothing records that Hindi v1 was translated from English v2 and is now stale. Needs a `translated_from_version_id` + "stale translation" state. | 05, 06 |
| I-4 | 🟠 | **Taxonomy table holds one row of columns** (`subject_id, chapter_id, topic_id, concept_id`) but AI tagging returns *multiple* concept tags, and doc 25 wants "primary topic + supporting concepts". Needs a many-to-many assignment with `is_primary`/weight. | 06, 11, 25 |
| I-5 | 🟠 | **State lists differ.** Doc 09 has SUPERSEDED; doc 27 doesn't. REJECTED has no exit (back to DRAFT? new version?). ARCHIVED "from any eligible" state is undefined. | 09, 27 |
| I-6 | 🟠 | **Master has a `status`** but lifecycle lives on versions. What does a Master's status mean? | 05, 06 |
| I-7 | 🟠 | **Test eligibility** is "APPROVED or PUBLISHED according to policy" and also "recommended PUBLISHED only". Pick one default. | 13 |
| I-8 | 🟠 | **Ingestion item state machine** starts at UPLOADED/PROCESSING, which are *file* states, not *item* states. Separate the file, batch and item state machines. | 27 |
| I-9 | 🟠 | **Passages** ("store separately and link dependent questions") have no table. | 07, 06 |
| I-10 | 🟢 | Review tasks, reviewer assignment, comments and checklists are described but have no tables. | 09, 06 |
| I-11 | 🟢 | Permanent ID "7–8 alphanumeric" — should use an alphabet without look-alikes (0/O, 1/I/l), e.g. Crockford Base32, plus a uniqueness retry. | 05 |

---

## 3. Missing areas (by domain)

### 3.1 🔴 Platform & API for many clients (your main concern)
The spec has one web app calling one API. A multi-client platform also needs:
- **API consumers defined**: first-party apps (studio web, admin, student app, exam client) vs.
  partner/third-party systems. Each has different auth, rate limits and stability guarantees.
- **API contract-first**: an **OpenAPI 3.1** file as the source of truth, reviewed before code, with
  generated typed SDKs for each frontend. Today the API is only a list of URLs.
- **API style guide**: naming, errors, pagination, filtering, long-running operations, versioning and
  deprecation policy (industry references: Google AIP, Microsoft REST API Guidelines, Zalando guidelines).
- **Machine-to-machine auth**: OAuth2 client credentials / API keys with scopes for partner systems.
- **Webhooks / events out**: e.g. "test published", "results ready" for other systems.
- **Missing endpoints**: taxonomy CRUD, sources, asset upload (pre-signed URLs), review tasks/comments,
  audit queries, AI registry admin, exports, notifications, passages, users/roles admin.
- **A rendering contract**: the same question (LaTeX, diagrams, tables) must look identical in web,
  Android and iOS. Needs a defined content-block schema and a shared renderer (or server pre-rendering).

### 3.2 🔴 Identity, tenancy and organization structure
- Users today = staff only. **Students** are a different population (potentially lakhs/millions, often
  phone-OTP login, often minors). **Parents** may need access.
- Real coaching structure is missing: **Organization → Centres/Branches → Courses → Batches → Enrollments**.
- Is the business **one organization internally**, or **SaaS sold to many institutes**? Can content be
  **shared/licensed across tenants** (e.g. a platform-owned master bank)? This changes the data model.
- Auth decision (build vs. buy an identity provider; sessions vs. tokens) is still open.

### 3.3 🔴 Assessment delivery / live exam engine (not specified at all)
A live exam is the hardest part technically, and nothing about it is specified yet:
- **Spiky load**: e.g. 50,000 students press "Start" at 10:00:00. Needs pre-generated papers, caching/CDN,
  load-tested capacity.
- **Server-authoritative timer**, section-wise time limits, late join and grace rules.
- **Autosave of every response**, resume after network loss or device crash, idempotent writes.
- **Security**: never send answer keys to the client, per-student question/option shuffling,
  paper release at start time, encrypted payloads, optional proctoring/lockdown browser, IP/device rules.
- **Marking schemes**: JEE Main (+4/−1), JEE Advanced partial marking for multi-correct, numerical tolerance,
  bonus marks, dropped questions.
- **Post-exam**: answer-key challenge window, re-evaluation, re-scoring after key changes, ranks,
  percentiles, normalization across shifts.
- Online-at-home vs. centre-based CBT vs. offline (OMR) modes.

### 3.4 🟠 Learning, analytics and personalization
Only sketched. Missing: practice mode, assignments/homework, event schema (what is logged per attempt),
a data warehouse/analytics pipeline, **difficulty calibration from real attempts** (Item Response Theory),
dashboards for faculty and parents, and recommendation rules.

### 3.5 🔴 Non-functional requirements (NFRs) — no numbers anywhere
Needed per module: expected data volume (questions, students, attempts), peak concurrent users,
latency targets (e.g. p95 < 300 ms for reads), availability target (e.g. 99.9% for the exam engine),
**RPO/RTO** (how much data loss and downtime is acceptable), cost budget per month, AI budget.

### 3.6 🔴 Privacy & compliance
- **India's DPDP Act 2023 + DPDP Rules**: student personal data, **verifiable parental consent for under-18s**,
  purpose limitation, data-principal rights, breach notification. Not mentioned.
- **Data residency** (keep data in India?), retention periods, deletion workflows.
- **Copyright** of imported third-party material (doc 21 notes legal review needed).
- A **threat model** (e.g. STRIDE) and a **privacy impact assessment** are missing.

### 3.7 🟠 Domain details still undefined
- Exact **JSON schema for content blocks** and **answer per question type** (numerical tolerance/range,
  match-the-column mapping, assertion-reason options, passage linkage).
- **Exam/PYQ catalogue** as an entity (JEE Main 2024, Session 1, 27 Jan, Shift 2), not free text.
- **Taxonomy versioning** — syllabi change (e.g. NCERT rationalised chapters); old questions must stay valid.
- **Difficulty 1–10 and Bloom level** have no definitions or rubric, so different reviewers will tag inconsistently.
- **Video solutions** source of truth (YouTube? own CDN? DRM?).
- Notifications (in-app/email/WhatsApp), comments/@mentions, task assignment.
- **Interoperability standards**: IMS **QTI 3.0** (question/test interchange) for import/export,
  **LTI 1.3** if other LMSs embed your tests.

### 3.8 🟠 Engineering process (what keeps it from becoming "vibe coded")
spec-v0 has good principles but no concrete rules. Missing:
- Repository layout (monorepo), module-boundary rules and how they are **enforced automatically**.
- API style guide, coding conventions, folder conventions, naming per module.
- Definition of Ready / Done per story, PR template, review checklist, CODEOWNERS, branch protection.
- Test strategy with concrete tools and coverage expectations; test data/fixtures.
- Release strategy (feature flags, canary/blue-green, rollback), runbooks, on-call, incident/post-mortem process.
- Rules for **AI-assisted coding** (spec → small tasks → tests → human review; an `AGENTS.md`/`CLAUDE.md`
  so AI tools follow the same conventions).

### 3.9 🟢 Product/operations
Personas and **user journey maps**, UI wireframes, onboarding of a new institute, billing/plans (out of MVP but
affects tenancy), support tooling/impersonation with audit, i18n of the UI itself (not just content).

---

## 4. Decisions still open (become ADRs)

| Decision | Options in spec-v0 | Depends on |
|---|---|---|
| Auth / identity provider | session vs JWT; build vs buy | Q5, Q6 in open questions |
| Queue technology | Redis / Postgres / SQS | exam-engine scale |
| Object storage | S3 / Supabase Storage | cloud choice |
| Backend framework | "TypeScript application layer" | team skills |
| API inside Next.js or separate service | unclear | multi-client requirement → **separate** |
| Row Level Security | optional | tenancy model |
| Hosting | EC2 → Kubernetes | budget, team ops skill |
| Document extraction | not chosen (build vs buy, e.g. Mathpix/Docling) | quality bar, cost |
| Test snapshot vs reference | "recommended snapshot + hash" | exam integrity |
