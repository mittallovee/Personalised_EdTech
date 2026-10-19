# Product Requirements — Our Baseline (v1)

> Status: **Draft for owner review** · Owner: product owner · Engineering: Claude Code (writes code), Codex (optional reviewer)
> Inputs: ideas and confirmed policies from [`spec-v1`](../spec-v1/docs/README.md) and [`spec-v0`](../spec-v0/), plus our own
> review ([06](../review/06-review-of-spec-v1.md)). From now on **this document is the source of truth**; the spec packs are
> reference material only.
>
> Each requirement has an ID, a **phase** (P1 = Phase 1, P2 …) and an origin:
> **[S]** taken from the spec packs · **[N]** new from the owner · **[R]** our recommendation (owner may veto).
> Phase details are in [02-phase-plan](./02-phase-plan.md).

---

## 1. Product in one paragraph

A multi-coaching (multi-tenant) **question bank platform**. Faculty create questions by hand or by uploading
PDF/Word/image files; AI extracts, tags, translates, solves and checks them; people review, approve and publish
them; published questions become a reliable, searchable, versioned bank. Later phases build tests and papers,
a student app, online/live exams, analytics, courses and personalized AI teaching on top of the **same backend API**.

## 2. People (personas & roles)

| Role | Who | Key needs |
|---|---|---|
| Platform admin | You (the SaaS operator) | Create coachings, full access to all, support, configuration |
| Coaching Owner | Head of an institute | Manage admins, settings; owns the coaching's data |
| Coaching admin | Academic head / coordinator | Manage faculty, grants, taxonomy, AI settings and budgets |
| Faculty | Teacher / content creator | Create, import, fix, review questions quickly |
| (Later) Student, Parent, Invigilator, Partner system | — | Phases 4–5 |

Formal actions are **grants**, not roles: `QC`, `APPROVE`, `PUBLISH`, `EDIT_OTHERS`, and new `MANAGE_AI_PROMPTS`.
Admins/Owner hold all grants implicitly.

---

## 3. Functional requirements

### A. Platform & tenancy

| ID | Requirement | Phase | Origin |
|---|---|---|---|
| A-01 | Multi-coaching architecture; every coaching's data fully isolated (DB row-level security + tenant checks) | P1 | S |
| A-02 | Start with one coaching; onboarding more must need no code change | P1 | S |
| A-03 | First platform admin created by a one-time command-line bootstrap (no public sign-up) | P1 | R |
| A-04 | Platform admin creates a coaching (name, logo, timezone) and its first Owner; only platform admin edits name/logo | P1 | S |
| A-05 | One common app URL; after login the user sees their coaching's name/logo | P1 | S |
| A-06 | Platform admin can act inside any coaching via an explicit "acting in coaching X" context; every action audited | P1 | S |
| A-07 | Coaching status: active / suspended (suspended = no login, data kept) | P1 | R |
| A-08 | One-time independent copy of a coaching's educational dataset to another coaching (new codes, no users/keys, no sync) | P2 | S |
| A-09 | Coaching data export (questions + metadata + assets) in a documented format (JSON; QTI 3.0 later) | P3 | R |

### B. Identity & access

| ID | Requirement | Phase | Origin |
|---|---|---|---|
| B-01 | Email + password login (Argon2id hashing, rate limiting, lockout delays) | P1 | S |
| B-02 | Google login (OIDC) | P1 | S |
| B-03 | Mobile OTP login | P2 | S — moved to P2: needs SMS vendor and India **DLT** template registration |
| B-04 | Several login methods linked to one account, only through verified linking (never auto-merge by matching email/phone) | P1 | S |
| B-05 | Admin invites faculty → one-time activation link (24 h) shown in the app to copy/share; no emails sent | P1 | S |
| B-06 | Password reset in P1 = admin generates a reset link; self-service reset (email/OTP) in P2 | P1/P2 | R — gap: spec forbids notification emails but self-reset needs a channel |
| B-07 | Each faculty belongs to exactly one coaching (no switcher) | P1 | S |
| B-08 | Owner appoints/removes admins (removal → demote to faculty or remove from app); transfers ownership to another admin | P1 | S |
| B-09 | Any admin invites/removes ordinary faculty and sets their grants | P1 | S |
| B-10 | Removing a user revokes access everywhere immediately; their content and history stay with the coaching | P1 | S |
| B-11 | Concurrent sessions (laptop + mobile); idle 12 h / absolute 7 d (configurable); logout | P1 | S |
| B-12 | Two-factor authentication for platform admins | P2 | R |
| B-13 | Token-based login (OAuth2/OIDC + PKCE) for mobile/student/exam/partner apps — **designed in P1**, built with the first non-web client | P4 | R |

### C. Taxonomy & catalogues

| ID | Requirement | Phase | Origin |
|---|---|---|---|
| C-01 | Hierarchy: class → subject → chapter → topic → optional subtopic | P1 | S |
| C-02 | Concepts: one primary + any number of secondary per question; secondary may sit outside the primary topic (same subject) | P1 | S |
| C-03 | Admin create/edit/deprecate nodes; **bulk import from Excel/CSV** to seed the JEE/NEET Physics syllabus quickly | P1 | R |
| C-04 | Deprecated nodes stay valid for old questions (syllabus changes never break history) | P1 | R |
| C-05 | AI may add a missing concept immediately as "provisional"; admins get an in-app review item (approve/edit/merge/revoke) | P1 | S |
| C-06 | Alias matching before AI creates a concept (avoid "Newton's 2nd law" vs "Newton's second law") | P1 | R |
| C-07 | Prerequisite graph between concepts (same subject, may cross classes, no cycles); AI-proposed, admin-reviewed | P2 | S |
| C-08 | Faculty concept-graph view; open questions linked to a concept | P2 | S |
| C-09 | Concept merge with redirect of future use; history preserved | P2 | S |
| C-10 | Localized labels for taxonomy in each enabled language | P1 | S |
| C-11 | **Exam catalogue**: exam (JEE Main, JEE Advanced, NEET, CBSE…), year, session, date, shift, paper code — managed by admin | P1 | R — gap: spec references exam IDs but no owner |
| C-12 | **Bloom level** fixed catalogue (Remember … Create) and a written **difficulty 1–10 rubric** shown in the editor | P1 | R — gap: undefined scale → inconsistent tagging |
| C-13 | **Source catalogue** (book, module, test series, PYQ paper) for attribution of manually entered questions | P1 | R |

### D. Question authoring & content

| ID | Requirement | Phase | Origin |
|---|---|---|---|
| D-01 | Nine formats: SCQ, multiple-correct, integer, single digit, numerical, matching, assertion–reason, multiple-statement, passage-based group | P1 | S |
| D-02 | Answer rules per spec-v1 (SCQ exactly 1 of 4; multi-correct ≥1 of 4; integer 0–999; single digit 0–9; numerical 0.00–999.00 exact or one range, 2 decimals, never silently rounded; matching rules; etc.) | P1 | S |
| D-03 | Those limits are **configuration with defaults** (per format, overridable per exam), not hard-coded; owner will check PYQs for negatives/>999 | P1 | R + owner agreed |
| D-04 | Structured content blocks: paragraph, equation, image, table, list | P1 | S |
| D-05 | Equation entry: **LaTeX** and **visual editor** with live preview | P1 | S |
| D-06 | MathML paste/import | P2 | S — moved to P2 (rarely typed by hand; conversion needs evaluation) |
| D-07 | Images/diagrams: upload, crop, alt text; immutable once used by a published version | P1 | S |
| D-08 | Solution (text/steps) optional; video solution = optional external link | P1 | S |
| D-09 | Incomplete drafts save; autosave; warn before leaving unsaved | P1 | S |
| D-10 | **Preview exactly as a student will see it** (same renderer later used by student apps) | P1 | R |
| D-11 | Identity: internal UUID + permanent global **8-character code** (A–Z, 0–9) + versions + immutable revisions | P1 | S |
| D-12 | Correcting a published question → new version, same code; variant/translation → new code with link to source version | P1 | S |
| D-13 | **"Source updated" flag** on translations/variants when their source gets a newer published version | P1 | R |
| D-14 | Passage group: shared passage, each child its own code and answer type | P1 | S |
| D-15 | Metadata: class, subject, chapter, topic, subtopic, concepts, language, difficulty, Bloom, PYQ (exam, year, date, shift, paper code), source | P1 | S |
| D-16 | Automatic duplicate check on every new question: exact + fuzzy (P1), semantic/embedding (P2); human decides; exact duplicate → attach source to existing question | P1/P2 | S |
| D-17 | Bulk edit (metadata), bulk submit, bulk grant-respecting actions | P2 | R |
| D-18 | Comments thread on a question (beyond QC findings) | P3 | R |

### E. Review & publication workflow

| ID | Requirement | Phase | Origin |
|---|---|---|---|
| E-01 | States: DRAFT → IN_REVIEW → (CHANGES_REQUESTED ↺) → QC_PASSED → APPROVED → PUBLISHED; archive/restore as separate availability flag | P1 | S |
| E-02 | Each formal action needs its grant; one person may do all if granted | P1 | S |
| E-03 | Coaching setting "reviewer must differ from author" (off by default) | P2 | R |
| E-04 | Approvals bind to the exact revision; any edit sends the version back to DRAFT | P1 | S |
| E-05 | Shared review queue with filters (subject, chapter, author, age, language) | P1 | S |
| E-06 | Return-for-correction needs structured reasons + note | P1 | S |
| E-07 | Publication checklist (answer valid, class, subject, one chapter, one topic, primary concept, difficulty, Bloom, PYQ exam/year if PYQ) | P1 | S |
| E-08 | Revision diff view (what changed between two revisions/versions) | P1 | R |
| E-09 | Per-question history timeline (audit) | P1 | R |
| E-10 | Archive/restore by creator (own) or admin | P1 | S |

### F. Bank & search

| ID | Requirement | Phase | Origin |
|---|---|---|---|
| F-01 | Paginated bank list with filters (all metadata, state, language, format, has-solution, has-video, PYQ) and live **count** | P1 | S |
| F-02 | Lookup by 8-character code | P1 | S |
| F-03 | Free-text search (stem, options, solution) + fuzzy search (typos) | P1 | R — gap in spec |
| F-04 | Semantic ("find similar") search | P2 | R |
| F-05 | Saved filters / views | P3 | R |

### G. Document ingestion

| ID | Requirement | Phase | Origin |
|---|---|---|---|
| G-01 | Upload PDF, DOCX, images (JPEG/PNG/WebP/HEIC); 50 MB per document, 10 MB per image; many files at once | P1 | S |
| G-02 | Legacy .DOC (converted in an isolated sandbox) | P2 | S |
| G-03 | Background jobs: user keeps working; progress per file; cancel own job; retry; partial results kept | P1 | S |
| G-04 | AI extraction (page images + text → structured candidates) for printed and scanned pages, with source page/region anchors, equations, diagrams | P1 | S |
| G-05 | Handwritten questions/solutions: supported through the same path in P1 ("best effort"), measured and tuned in P2 | P1/P2 | S |
| G-06 | **Side-by-side review**: source page · extracted question · metadata/duplicates; keyboard shortcuts | P1 | S (spec-v0) |
| G-07 | Separate answer-key/solution files automatically paired to the paper; faculty can fix pairing | P2 | S |
| G-08 | **Adaptive layout patterns** (learn a layout once, reuse to cut AI cost) | P2 | S — it's a cost optimisation; we first measure real cost in P1 |
| G-09 | Originals kept until admin deletes; faculty can view originals | P1 | S |
| G-10 | Admin storage dashboard + safe original deletion (questions and needed diagrams survive) | P2 | S |
| G-11 | **Golden evaluation set**: during M6 the owner uploads real files through the app; with owner approval a subset of reviewed results becomes the reference set used to measure extraction quality before/after every change | P1 | R + owner |

### H. AI platform

| ID | Requirement | Phase | Origin |
|---|---|---|---|
| H-01 | Providers: Anthropic, OpenAI, Google, OpenRouter behind one internal adapter interface; more later | P1 | S |
| H-02 | Each coaching enters its own API keys (encrypted, write-only, masked) | P1 | S |
| H-03 | Admin enables models + default per operation; faculty picks among enabled compatible models | P1 | S |
| H-04 | Bounded, visible fallback to another enabled model using the same coaching's keys | P1 | S |
| H-05 | Usage & cost ledger (actual / estimated / unknown), per faculty and operation | P1 | S |
| H-06 | Monthly per-faculty budget: warn at 80 %, stop new AI work at 100 %, reset on the 1st (Asia/Kolkata) | P1 | S |
| H-07 | AI metadata tagging (fills fields directly; human can change) | P1 | S |
| H-08 | AI translation on request → new linked question (own code, own review) | P1 | S |
| H-09 | AI solve missing answer (on request) | P1 | S |
| H-10 | **AI verification** of a question (stem, options, answer, solution, units/signs) → findings + suggested fix; per-question opt-in "apply correction" showing old/new/reason. User chooses prompt (coaching default / personal / one-off custom) and model per run | P1 | S + N |
| H-11 | AI variant generation (count, mixed target type/difficulty, instructions; keeps primary concept) | P2 | S |
| H-12 | AI diagram generation/editing | P2 | S |
| H-13 | **AI Prompt Library**: every user can view prompts (verification, translation, solve, tagging, extraction), save **personal** prompts or use a one-off custom prompt per run; authorized users change the coaching default — versioned, testable, rollback | P1 | **N** — see [03-ai-prompt-library](./03-ai-prompt-library.md) |
| H-14 | **Translation glossary** per coaching per language (e.g. velocity → वेग) automatically given to the translation prompt | P1 | R |
| H-15 | Every AI run records model, prompt version, input revision, output, cost; AI output never counts as human QC | P1 | S |
| H-16 | AI quality dashboard: acceptance/correction rates per operation, model and prompt version | P2 | R |
| H-17 | **Live model catalogue**: the list of models is fetched from each provider's model-list API with the coaching's key (refresh on demand + daily), so users always choose from what the provider offers *today*; admin enables models; capability (text/vision/JSON) and price info come from provider data or an admin-editable overlay; unknown price → cost shown as "unknown", budget rules still apply | P1 | **N** |
| H-18 | **Economy AI runs (batch mode)**: for work that is not urgent, a run can use the provider's Batch API (Anthropic, OpenAI, Google and OpenRouter offer one, typically about half price with results within 24 hours, often much sooner). Each run offers "Now (normal price)" or "Economy (about half price, done within 24 h)"; admins set the default per operation; Economy appears only for **models** that support batch and have a known price (support, discount and price are recorded per model in the H-17 catalogue, since providers decide this model by model). The user keeps working; each run remembers the question revision it was based on (H-15). Budgets (H-06) reserve the estimated cost at submission, and every ending settles the reservation: success replaces it with the actual charge, while cancelled, expired or failed batches release it (keeping only any charge the provider actually made), so a dead batch never blocks the budget. When results arrive they are recorded like any other run (H-05 ledger at the actual discounted cost) and applied **only if the question is still at that revision and the submitter is still allowed to make that change** (B-10); otherwise the result is kept unapplied (**"out of date"** or **"needs review"**) for an authorised user to review, apply by hand or re-run, and never overwrites newer work. A batch is submitted at most once, even after a crash or a cancellation in flight; a run whose submission outcome is unknown is reconciled with the provider, never silently re-sent (N-05; see ADR-0009). An in-app notification (I-01) links to the results. Economy runs can be cancelled while waiting (a result that still arrives after cancelling is kept but never applied); expired or failed batches are reported, never silently retried at full price | P1 | N (19 Oct) |

### I. Notifications, admin & audit

| ID | Requirement | Phase | Origin |
|---|---|---|---|
| I-01 | In-app notifications only (no emails): review returned, taxonomy review needed, budget 80 %/100 %, job finished/failed, prompt changed | P1 | S |
| I-02 | Admin console: users & grants, taxonomy, exams/sources, AI keys/models/prompts, budgets, usage reports | P1 | S |
| I-03 | Audit log (who did what, when, before/after) — viewable by admins, per question and globally | P1 | S |

### J. Later phases (summary — detailed discovery happens at each phase)

| ID | Capability | Phase |
|---|---|---|
| J-01 | Test builder (filters, counts, blueprints, sections, marking schemes, one-per-master rule) + paper export (PDF/Word, answer key, solutions) | P3 |
| J-02 | Students: identity (OTP), batches/courses enrollment, parental consent (DPDP Act), student app (web + Android/iOS), practice mode, assignments; payments/subscriptions | P4 |
| J-03 | Online tests & live exam engine (CBT): scheduling, server timer, autosave, shuffling, results, ranks, answer-key challenges | P5 |
| J-04 | Learning analytics: per-question timing, concept mastery, difficulty calibration from real attempts (IRT), recommendations | P6 |
| J-05 | Courses, live classes, recorded sessions | P7 |
| J-06 | Personalized AI teaching and concept videos | P8 |

---

## 4. Non-functional requirements

| ID | Area | Requirement (P1 targets are proposals — confirmed when measured) |
|---|---|---|
| N-01 | Isolation | No cross-coaching read/write possible; automated tests try it on every change |
| N-02 | Security | OWASP Top 10 controls; secrets never in code/logs/browser; uploads validated by content, size and type; rendered content sanitized |
| N-03 | Performance | Bank list/filter/count p95 < 500 ms at 1 lakh questions in one coaching (to be measured on a synthetic fixture) |
| N-04 | Scale | Design for lakhs of questions per coaching and many coachings; no full-bank loads into browser or memory |
| N-05 | Reliability | Jobs survive restarts; retries never duplicate; every state change is transactional |
| N-06 | Backups | Daily DB + files backup, off-machine copy, **restore tested** before real data is relied on |
| N-07 | Observability | Structured logs with request/job IDs, metrics (API, jobs, AI cost), error tracking, health checks |
| N-08 | API | Versioned REST `/api/v1`, OpenAPI contract in repo, no breaking changes without a new version |
| N-09 | Browsers/devices | Latest Chrome/Edge/Firefox/Safari; desktop-first, usable on tablet; phone for viewing |
| N-10 | Accessibility | Keyboard navigation, labels, contrast, alt text for diagrams |
| N-11 | UI language | English UI in P1 (question content in all 7 languages); Hindi UI later if wanted |
| N-12 | Privacy | Minimal personal data; DPDP Act applies to faculty data now and student data (incl. minors' consent) from P4 |
| N-14 | Hosting | Development on the owner's PC (Docker); later a cloud (AWS or Google Cloud) using its **managed PostgreSQL** (RDS / Cloud SQL — both support pgvector) and object storage (S3 / GCS). Code stays cloud-neutral: containers, storage interface, config via environment |
| N-13 | Maintainability | Engineering standards, CI gates, module boundaries enforced, ADRs for decisions (see `docs/engineering/`, next deliverable) |

## 5. Decisions taken (this round)

| # | Decision |
|---|---|
| 1 | Claude Code writes code with the owner; Codex may review PRs; owner approves merges |
| 2 | Tech stack: Claude Code proposes (see phase plan §4); final after owner review |
| 3 | API design delegated to engineering: API-first, cookie sessions for web now, token auth later, OpenAPI contract |
| 4 | Answer limits configurable with spec-v1 values as defaults; owner checks PYQs |
| 5 | New: AI Prompt Library in Phase 1 |
| 6 | Spec packs are input only; this document set is the baseline |
| 7 | "QC prompt" = AI verification prompt: users can view it, save their own, or type a one-off prompt, and choose the model per run (18 Oct) |
| 8 | Models come from providers' live model lists, not a fixed list (18 Oct) |
| 9 | Develop on owner's PC; later cloud (AWS/GCP) with managed database (18 Oct) |
| 10 | Sample files arrive through the app's upload during M6 (18 Oct) |
| 11 | OTP login and self-service password reset in Phase 2 (18 Oct) |
| 12 | After Phase 1, Phase 2 (ingestion at scale & AI) comes next (18 Oct) |
| 13 | Economy (batch) AI runs in Phase 1, M5: user picks per run, admins set defaults per operation, in-app notification when done (19 Oct, H-18) |

## 6. Still open — owner input needed

See the end of [02-phase-plan](./02-phase-plan.md#7-open-questions-for-the-owner).
