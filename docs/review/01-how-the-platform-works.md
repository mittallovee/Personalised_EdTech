# 01 — How the Platform Works (Plain-Language Walkthrough)

> Status: **Review draft** — written from `docs/spec-v0/` (the original 36-document pack).
> Purpose: give the product owner a single, end-to-end mental model of the system before we refine the specs.

---

## 1. One-paragraph summary

The spec describes a **multi-tenant content platform** (a "question bank CMS") for coaching institutes.
Faculty upload PDFs/Word files of questions, the system **extracts** each question into structured data,
humans **check** the extraction, the question goes through a **review → approve → publish** workflow,
AI helps at many steps (tagging, translating, solving, finding duplicates), and finally a **Test Builder**
assembles published questions into tests. Students taking tests is planned only as a *future* layer.

In industry terms, what is specified today is the **authoring side** (content production).
The **delivery side** (students practising, live exams, results, analytics) is mostly not yet specified.

---

## 2. Who uses it (actors / personas)

| Actor | What they do | Spec status |
|---|---|---|
| Platform Admin | Runs the whole SaaS: tenants, AI model registry, system settings | Specified |
| Organization Admin | Manages one institute's users, roles, settings | Specified |
| Creator / Faculty | Uploads documents, creates and edits draft questions | Specified |
| Reviewer / Validator | Checks correctness of answer, solution, metadata, diagrams | Specified |
| Approver / Publisher | Gives final approval and publishes | Specified (some conflicts — see 02) |
| Test Creator | Builds tests from published questions | Specified |
| Student | Practises, takes live exams, sees results | **Future, ~1 page only** |
| Parent, Centre manager, Invigilator, Partner system | — | **Not mentioned** |

---

## 3. The core idea: Master → Variant → Version

This is the most important concept in the whole design. A concrete Physics example:

```text
Master Question  Q7K2M9P        "Block on a rough incline — find acceleration"
│                                (identity only — never changes, no text stored here)
│
├── Variant A  (original, imported from JEE Main 2019)
│     m = 2 kg, θ = 30°, μ = 0.2   → answer: 2.6 m/s²
│     ├── Version 1  English  (imported, had a typo)        → SUPERSEDED
│     ├── Version 2  English  (typo fixed)                  → PUBLISHED
│     └── Version 1  Hindi    (AI-translated, reviewed)     → PUBLISHED
│
└── Variant B  (AI-modified numbers)
      m = 5 kg, θ = 37°, μ = 0.3   → different answer
      └── Version 1  English                                → IN_REVIEW
```

- **Master** = "the same underlying question idea". Has a permanent random ID (like `Q7K2M9P`).
  Changing chapter tags, language or wording never changes this ID.
- **Variant** = a separately usable question from the same idea (different numbers/scenario).
- **Version** = a frozen snapshot of a variant's content at one point in time, in one language.
  **Published versions are never edited** — a fix creates a new version (this is called *immutability*).

Why this matters: tests that were already given keep pointing to the exact content students saw;
duplicates are controlled ("max one question per Master in a test"); and analytics later can be grouped by concept.

---

## 4. End-to-end flow (the life of a question)

```text
 ┌───────────── AUTHORING SIDE (specified) ──────────────┐   ┌──── DELIVERY SIDE (future / not specified) ────┐
 │                                                        │   │                                                │
 │  PDF/DOCX ──► Ingestion Batch ──► Workers extract      │   │                                                │
 │                                  (pages, text, maths,  │   │                                                │
 │                                   diagrams, answers)   │   │                                                │
 │                       │                                │   │                                                │
 │                       ▼                                │   │                                                │
 │            Staging "Ingestion Items"                   │   │                                                │
 │            (NOT yet in the question bank)              │   │                                                │
 │                       │                                │   │                                                │
 │                       ▼                                │   │                                                │
 │        Ingestion QC (3-panel screen: source PDF |      │   │                                                │
 │        extracted question | metadata + duplicates)     │   │                                                │
 │        Decision: New Master / Existing Master /        │   │                                                │
 │                  Variant / Duplicate / Reject          │   │                                                │
 │                       │                                │   │                                                │
 │   Manual creation ────┤                                │   │                                                │
 │   AI generation  ─────┤                                │   │                                                │
 │                       ▼                                │   │                                                │
 │   DRAFT ─► IN_REVIEW ─► APPROVED ─► PUBLISHED          │   │                                                │
 │               │                        │               │   │                                                │
 │               └─► REJECTED             ▼               │   │                                                │
 │                                Search / Question Bank  │   │                                                │
 │                                         │              │   │                                                │
 │                                         ▼              │   │                                                │
 │                       Test Builder (filters, counts,   │   │   Exam scheduling ─► Student starts test        │
 │                       variant policy, sections)        │──►│   ─► answers autosaved ─► submit ─► scoring    │
 │                                         │              │   │   ─► results / ranks ─► analytics              │
 │                                         ▼              │   │   ─► recommendations ─► (feeds difficulty      │
 │                       Published Test Version           │   │       back into the question bank)             │
 │                       (immutable snapshot + hash)      │   │                                                │
 └────────────────────────────────────────────────────────┘   └────────────────────────────────────────────────┘
```

### 4.1 Ingestion (spec docs 07, 08)
1. Faculty creates a **batch** (name, subject, exam, year, language, source).
2. Uploads files → system checks real file type (not just extension), virus-scans, stores the original, records a SHA-256 hash.
3. Background **workers** extract pages and blocks with coordinates, split into questions, pull out diagrams and equations, detect the answer.
4. AI proposes metadata (chapter, topic, difficulty) and the system searches for possible duplicates.
5. Each candidate gets **field-level confidence** (e.g. stem 0.99, answer 0.72). Low-confidence items go to "detailed review", high-confidence to "fast review".
6. A reviewer decides the item's identity (New / Existing Master / Variant / Duplicate / Reject). Only then is it written into the real question bank as a DRAFT.

Key principle: **raw extraction never goes straight into the production bank** (ADR-005 "staging").

### 4.2 Content review & publication (doc 09, 27)
- Ingestion QC asks: *"Did we copy the source correctly?"*
- Content QC asks: *"Is this a correct, good question we're willing to publish?"*
- A checklist must pass (answer verified, taxonomy assigned, difficulty set, required solution present, etc.).
- Two reviewers disagreeing → CONFLICT → expert resolution.
- On publish: content frozen, content hash generated, actor and time recorded.

### 4.3 AI platform (doc 10, 11)
```text
Feature asks for "TAG_QUESTION"
  → AI Orchestrator: checks policy (is this org allowed? budget left?)
  → picks model (default or user's allowed choice) and prompt version
  → calls AI Gateway (LiteLLM) → provider or local model
  → validates JSON output against a schema, then against domain rules
  → stores provenance (model version, prompt version, tokens, cost, who asked)
  → human accepts / edits / rejects the suggestion
```
Business code never contains model names; it asks for an **action** and configuration decides the model.

### 4.4 Search & duplicates (doc 12)
Exact ID lookup → full-text → fuzzy (typos) → later semantic (embeddings).
Duplicate score combines text, meaning, options and structure; thresholds are tuned on real data.

### 4.5 Test Builder (doc 13)
Filters (chapter, topic, difficulty, type, exam/year, has text solution, has video solution…) with a **live
"Available questions: 1,248" count**, a variant policy (`ONE_PER_MASTER` etc.), sections/blueprints, ordering,
and **immutable published test versions** that keep a snapshot/hash.

---

## 5. How the system is built (as proposed in spec-v0)

- **Modular monolith**: one deployable backend, internally split into clear modules
  (identity, tenancy, taxonomy, question bank, ingestion, review, AI, search, media, test builder, audit…).
- **PostgreSQL** for data, **object storage** (S3) for files, **queue + workers** for slow jobs,
  **LiteLLM** as AI gateway, **Next.js** web app, **Docker**, **Terraform**, EC2 first, Kubernetes later.
- **Outbox pattern** for reliable events, **explicit commands** (`PublishQuestionVersion`) instead of "PATCH status".
- REST API under `/api/v1` with standard error envelope, cursor pagination and idempotency keys.

These are sound, industry-standard choices. What's missing or unclear is covered in
[`02-gap-analysis.md`](./02-gap-analysis.md).
