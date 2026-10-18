# Phase 1 — What We Are Building

> Status: **Draft for owner review** · Detail behind each item: [01-requirements](./01-requirements.md) (IDs in brackets),
> build order: [02-phase-plan](./02-phase-plan.md).

## 1. The promise of Phase 1

> *A coaching can move its Physics questions, existing papers and new questions alike, into one clean,
> reviewed, searchable, versioned question bank, with AI doing the heavy lifting and faculty in control.*

At the end of Phase 1 the app runs in the cloud, used by one coaching (more can be added without code
changes), with English/Hindi/Gujarati/Bengali/Marathi/Telugu/Tamil question content.

## 2. Who uses it and what they do

| Person | In Phase 1 they can… |
|---|---|
| **Platform admin** (you) | Create coachings and their Owner, set name/logo, act inside any coaching, see everything (audited) |
| **Owner** | Everything an admin can, plus appoint/remove admins and transfer ownership |
| **Admin** | Invite/remove faculty, give grants (QC, approve, publish, edit others' questions, manage prompts), manage syllabus/exams/sources, AI keys, models, prompts, budgets; see usage and audit |
| **Faculty** | Create and import questions, use AI tools, review/approve/publish if granted, search the bank, keep personal AI prompts |

## 3. Screens (the app you will see)

| # | Screen | What's on it |
|---|---|---|
| 1 | **Login** | Email + password, "Sign in with Google", activation-link page for new users |
| 2 | **Home / dashboard** | My drafts, items returned to me, review queue count, running upload jobs, AI budget used, notifications |
| 3 | **Question bank** | Table of questions with filters (class, subject, chapter, topic, concept, format, difficulty, Bloom, language, state, PYQ exam/year, has solution/video) and a live **count**; free-text and code search |
| 4 | **Question editor** | Choose format (9 types); stem, options/statements/matching columns/passage; equations by **LaTeX or visual editor**; images; answer; optional solution and video link; metadata; **student-style preview**; autosave |
| 5 | **Question detail** | Current version, all versions and revisions, **diff** between versions, history (who did what), AI runs (model + prompt used), linked translations/variants with "source updated" flag |
| 6 | **Review queue** | Questions waiting for QC/approval/publish; open one → checklist, findings, Pass / Return with reasons / Approve / Publish |
| 7 | **AI action dialog** | For verify, translate, solve, tag: pick **prompt** (coaching default / my prompts / one-off custom), extra instructions, **model** (live list), see estimated cost and budget left |
| 8 | **AI verification result** | Findings (e.g. "answer should be C, sign error in step 2"), suggested correction, old vs. new, *Apply to this question* (opt-in) |
| 9 | **Upload & jobs** | Drag-and-drop many PDF/DOCX/image files; per-file progress; cancel/retry; you keep working meanwhile |
| 10 | **Extraction review** (3 panels) | Original page · extracted question (editable) · metadata + possible duplicates; keyboard shortcuts; "Create question" / "Same as existing" / "Reject" |
| 11 | **Prompt library** | Every AI operation's prompt: view, versions, diff, test on a real question, my personal prompts; admins activate/rollback coaching default |
| 12 | **Admin console** | Users & grants · Syllabus (Excel import) · Exams · Sources · Languages & glossary · AI keys · Models (fetched live from providers, enable/disable, defaults) · Budgets · Usage & cost report · Audit log |
| 13 | **Platform console** | Coachings list, create coaching + Owner, branding, act-as-coaching |
| 14 | **Notifications** | In-app bell: returned questions, review items, budget 80/100 %, job finished/failed, prompt changed, new taxonomy item to review |

## 4. Main journeys (end to end)

**J1 — Set up:** platform admin creates the coaching and Owner → Owner signs in with the activation link →
invites faculty and admins → admin imports the Physics syllabus from Excel and adds exams/sources → admin
enters AI keys, fetches the provider model lists, enables models, sets budgets.

**J2 — Type a question by hand:** faculty opens the editor → picks "Numerical" → writes the stem with
equations → enters the answer 9.81 → AI tags chapter/topic/concepts/difficulty (faculty adjusts) →
preview → submit for review.

**J3 — Verify with AI (your "QC prompt"):** faculty clicks *Verify* → keeps the coaching prompt, or picks
"My strict numeric check", or writes a one-off prompt → chooses a model → sees findings → optionally
applies the suggested fix → the change shows old/new/reason and the question goes back to draft if it had
been reviewed.

**J4 — Review & publish:** reviewer opens the queue → checks the question → returns it with reasons or
passes QC → approver approves → publisher publishes → the version is frozen with its permanent 8-character
code. A later correction creates version 2 under the same code.

**J5 — Import an existing paper:** faculty uploads 10 PDFs and some photos → jobs run in the background →
extraction review screen shows each page beside the extracted question → faculty fixes, marks duplicates,
creates questions → they follow J4.

**J6 — Translate:** faculty translates a reviewed English question to Hindi (glossary applied, prompt and
model chosen) → a new linked Hindi question with its own code goes through review. If the English one is
corrected later, the Hindi one shows **"source updated"**.

**J7 — Tune a prompt:** admin opens the prompt library → edits the coaching translation prompt → tests the
draft on 3 questions against the current version → activates it → everyone's next translation uses it;
rollback is one click.

## 5. Included vs. not included

| Area | ✅ In Phase 1 | ⏭ Later |
|---|---|---|
| Login | Email/password, Google, activation links, admin reset links | Mobile OTP, self-service reset, 2FA (P2) · student/app tokens (P4) |
| Questions | All 9 formats, LaTeX + visual equations, images, passages, versions, preview, archive | MathML input, bulk edit (P2) · comments (P3) |
| Review | QC → approve → publish, return with reasons, diff, history | "Reviewer must differ" setting (P2) |
| Search | Filters + counts, free text, fuzzy, code lookup, exact/fuzzy duplicates | Semantic "find similar" (P2) · saved views (P3) |
| Taxonomy | Hierarchy, primary + secondary concepts, Excel import, exams, sources, Bloom, difficulty rubric, AI-provisional concepts | Prerequisite graph & graph view, concept merge (P2) |
| Upload | PDF, DOCX, images; background jobs; AI extraction (printed, scanned, handwriting best-effort); 3-panel review | Separate key/solution file pairing, legacy .DOC, layout-pattern reuse, handwriting tuning, storage dashboard & deletion (P2) |
| AI | 4 providers, live model lists, coaching keys, budgets, tagging, translation + glossary, solve, **verification**, **prompt library** | Variants, diagrams, AI quality dashboard (P2) |
| Platform | Multi-coaching, branding, act-as-coaching, audit | Coaching data copy (P2) · export (P3) |
| Students / tests / exams / courses | — | P3–P8 |
| Hosting | Your PC during development → cloud (AWS or Google Cloud, managed database) at the end of Phase 1 | Scaling, multi-region later |

## 6. Done means

Phase 1 is complete when:
1. All journeys J1–J7 work in the cloud deployment for a real coaching.
2. Automated tests cover every requirement marked P1, including attempts to read another coaching's data.
3. Extraction quality is measured on your uploaded files and accepted by you.
4. Backups are restored successfully in a drill.
5. Monitoring and alerts are live, and docs match the actual behaviour.
