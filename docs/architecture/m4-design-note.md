# M4 Design Note — Review & bank

> Status: **Draft for owner approval** · Milestone M4 of Phase 1 ([phase plan](../product/02-phase-plan.md))
> Requirements: E-01, E-02, E-04 to E-10, F-01 to F-03, D-12 (a correction is a new version), D-16 (exact and
> fuzzy duplicate check), I-01 (in-app notifications for returned and published questions), I-03 (per-question
> history) · Hardening items due with M4: K-07, K-08, K-16 (see §13)
> · ADRs 0005, 0008 (to be accepted), 0011, 0016, **0020 (new, workflow bound to a frozen revision)**
> · Builds on the [M3 design note](./m3-design-note.md)
> Reference input (never edited): `docs/spec-v1/docs/QUESTION_LIFECYCLE_AND_QC.md`, `PUBLICATION_REQUIREMENTS.md`,
> `DUPLICATE_AND_VARIANT_POLICY.md`, `QUESTION_ARCHIVAL.md`, `CAPACITY_AND_PERFORMANCE.md`

## 1. Goal

A question written in M3 can now travel to the bank: the author **submits** it, a reviewer **returns** it with
reasons or **passes QC**, another person (or the same one, if they hold the grant) **approves**, and someone
with the publish grant **publishes** it. A published question never changes; a correction is a new version
under the same code. Everyone in the coaching can then **search the bank**: filter by any label, look a
question up by its 8-character code, type words (even with a typo) and see how many questions match.

M4 is the milestone where **faculty start real work** (phase plan, "first real use"). That is why it also
carries the safety items that must exist before real content is typed: backups (K-16), a migration safety check
(K-07) and a measured search (K-08).

**What M4 does not do:** AI of any kind (M5), uploading papers (M6), translations and the "source updated" flag
(D-13, M5), the "reviewer must differ from the author" setting (E-03, P2), bulk actions (D-17, P2), comments
on a question (D-18, P3), saved filters (F-05, P3), "find similar" by meaning (F-04, P2).

## 2. What you will be able to do at the end of M4

1. As faculty: press **Submit for review** on a finished question. It freezes the exact text you wrote and
   appears in the shared queue. You are told in the app if it is returned, and when it is published.
2. As a person with the **QC** grant: see the queue (filter by subject, chapter, author, language, age), open a
   question, **return it** with structured reasons and a note, or **pass QC**.
3. As a person with the **APPROVE** grant: approve what passed QC. With the **PUBLISH** grant: publish what is
   approved. Admins and the Owner hold all three implicitly; one person may do every step if they hold every
   grant (E-02).
4. See **what changed** between any two saved versions of a question (a before-and-after view), and a
   **history** of who submitted, returned, passed, approved, published or archived it, and when.
5. **Correct a published question**: it becomes version 2 of the same code, a new draft; version 1 stays
   published and unchanged until version 2 is published.
6. **Search the bank**: filters (class, subject, chapter, topic, concept, difficulty, Bloom, format, language,
   state, past-year exam and year, has-solution, has-video, author, archived), a live count, free-text search
   over stem, options and solution that forgives typos, and a box that opens a question by its code.
7. See **possible duplicates** of a question (the same text, or very similar text) before it is submitted, with
   the two side by side, and record that it is or is not a duplicate. Nothing is ever merged or deleted
   automatically.

## 3. What is built where (modules)

| Module | Owns | Why separate |
|---|---|---|
| `questions` (extended) | The workflow state of a version, the pure state machine, the rule "a published version never changes", diff, the extraction of search facts from content | The state sits next to the revisions it protects, so the database trigger and the code agree on one rule |
| `review` (new) | Who may do each step (grants), return reasons, the append-only `review_decisions`, the queue, the history timeline | Policy and queue are about *people and decisions*, not about content; it calls `questions.public` and never touches its tables |
| `search` (new) | The bank index (`bank_index`), filters, counts, free-text and fuzzy search, duplicate candidates | A derived, rebuildable copy built for fast lookup (ADR-0008); never the source of truth |
| `notifications` (new) | In-app notifications (a table, a list, mark as read) | Used by M4 for "returned" and "published" and by M5/M6 later; knows nothing about questions |

Dependency direction (checked by import-linter): `review` → `questions.public`, `notifications.public`; `questions` →
`search.public` (to record index facts after every save); `search` → `taxonomy.public` (label names only).
No cycle: `questions` never imports `review`.

## 4. The workflow (E-01, E-02, E-04, E-06, E-07)

### 4.1 States and steps

```text
DRAFT ──submit──▶ IN_REVIEW ──pass QC──▶ QC_PASSED ──approve──▶ APPROVED ──publish──▶ PUBLISHED
  ▲                  │  ▲                    │                     │
  │                  ▼  │                    ▼                     ▼
  │          CHANGES_REQUESTED  ◀── return (by the holder of that step's grant) ──┘
  │                  │
  └── withdraw ◀─────┴──── (also from IN_REVIEW, QC_PASSED, APPROVED)
```

The state belongs to a **version** (M3 §5.1: master → version → revision). Archived/restored is a separate
flag on the master (already built) and does not change the state (E-01, E-10).

| From | Step | To | Who | Needs |
|---|---|---|---|---|
| DRAFT, CHANGES_REQUESTED | **Submit** | IN_REVIEW | Anyone who may edit it | No `error` finding; "still to do" items are allowed (spec: missing publication details show as findings at submit) |
| IN_REVIEW | **Return** | CHANGES_REQUESTED | QC grant | Reasons (at least one) and a note |
| IN_REVIEW | **Pass QC** | QC_PASSED | QC grant | The publication checklist is complete (§4.4) |
| QC_PASSED | **Approve** | APPROVED | APPROVE grant | Checklist still complete |
| QC_PASSED, APPROVED | **Return** | CHANGES_REQUESTED | APPROVE grant (from QC_PASSED), PUBLISH grant (from APPROVED) | Reasons and a note (§17, decision 3) |
| APPROVED | **Publish** | PUBLISHED | PUBLISH grant | The checklist is checked again, in the same database transaction |
| IN_REVIEW, QC_PASSED, APPROVED | **Withdraw** | DRAFT | The author, or anyone who may edit it | Nothing; the decisions so far stay in the history |
| PUBLISHED | **Start correction** | a **new version** in DRAFT | Anyone who may edit it | The new version starts as a copy of the published content |

Anything else is refused with `409 WORKFLOW_STEP_INVALID` (`details.state`, `details.allowed`). The table
above is one pure function (`questions/domain/workflow.py`), tested for every state × step; a database trigger
repeats the allowed pairs, so a bug in code cannot publish something that skipped QC.

### 4.2 The exact revision (E-04): why a stale approval cannot happen

- **Submit freezes the working revision** (the same freeze as *Save checkpoint*, M3 §5.1) and records its id
  as the version's **review revision**. QC, approval and publication all act on that one frozen revision. The
  reviewer is shown that frozen text, never the author's current working copy.
- The author's working copy is a new revision. While the question is IN_REVIEW, QC_PASSED or APPROVED the
  **editor is read-only** and offers **Withdraw to edit**. This keeps a stray keystroke (autosave runs every
  few seconds) from silently cancelling a review. The server enforces it as well: a save to a version that
  is not DRAFT or CHANGES_REQUESTED is refused with `409 QUESTION_NOT_EDITABLE`. (The spec says "any edit
  sends the version back to DRAFT"; withdrawing first is the same effect, made explicit. §17, decision 2.)
- After a withdrawal and a new submit, the review revision is the **new** frozen one. Old decisions stay in
  `review_decisions` bound to their old revision id; nothing in the code looks at them to authorise the new one.
- Every step except submit carries `If-Match` with the version's **workflow ETag** (`"flow-N"`, a counter that
  goes up on every state change). If two reviewers act at once, or the author withdrew a moment ago, the
  second request gets `412 REVISION_STALE` with the current ETag, and the screen reloads. The ETag for the
  working text (`"rev-N"`, M3) is a different value space, so the two cannot be mixed up. Submit uses the
  working text's ETag, like *Save checkpoint*.
- Each step locks the version row (`SELECT … FOR UPDATE`) and rechecks state and review revision inside the
  transaction, so two simultaneous requests cannot both succeed.

### 4.3 Reasons for return (E-06)

A return needs one or more reasons from a fixed list and a written note (at least 10 characters). Reasons are
stable codes so the web can show them and, later, count them: `ANSWER_WRONG`, `STATEMENT_UNCLEAR`,
`OPTIONS_FLAWED`, `SOLUTION_WRONG`, `LABELS_WRONG`, `DIFFICULTY_OR_BLOOM_WRONG`, `DUPLICATE`, `FORMATTING`,
`OTHER` (appendix; wording for you to approve). The note is plain text, shown as text, never as markup.

### 4.4 The publication checklist (E-07)

No new rules: the checklist **is** the findings engine from M3, run on the **frozen review revision** and
the coaching's **current** catalogue and answer limits. A question may pass QC, be approved and be published
only with **no `error` and no `incomplete` finding** (the "still to do" list already covers answer valid, class,
subject, one chapter, one topic, primary concept, difficulty, Bloom, and exam and year when it is a past-year
question). Warnings do not block; an item retired from the catalogue since the question was written is a
warning (C-04). The solution stays optional. Publish **runs the check again inside its transaction**, because
the catalogue or an answer limit may have changed since QC. The decision records the checklist result (the
finding codes, which were none) as evidence.

### 4.5 Published means immutable (the exit criterion)

- A trigger refuses any change to a PUBLISHED version's state, review revision or revisions, and refuses a new
  revision under it, **even for the table owner** (the pattern M3 used for frozen revisions). The runtime role
  has no DELETE right on any of these tables.
- A **snapshot of the labels** is stored at publication (`published_versions`: the English names of class,
  subject, chapter, topic, concepts, exam and source as they were that day). Renaming a syllabus item later
  does not change how a published question reads in history (spec: "taxonomy label … must not silently alter
  historical rendering"). Pictures cannot be deleted and passage checkpoints are frozen (M3), so they need no
  copy.
- **Start correction** creates version *n+1* under the same master and code, in DRAFT, with the published
  content copied as its first working revision. The master points at its **published version** (`published_version_id`)
  until the new version is published; then the pointer moves and the old version stays addressable. Only one
  working version per master (M3), so a second correction is refused while one is open
  (`409 CORRECTION_ALREADY_OPEN`, `details.version_id`).

### 4.6 Passages

A passage has no review of its own in M4 (§17, decision 5). A child question pins a frozen passage
checkpoint, so its text cannot change under a published question, and the reviewer reads the passage next to
the child (the M3 editor already shows it). A change to the passage means a new checkpoint and a new
submit of each child that should use it.

## 5. Who may do what (extends M3 §6 and the M2 table)

| Action | Faculty | With grant | Admin / Owner | Platform admin |
|---|---|---|---|---|
| Submit, withdraw, start a correction on a question you may edit | Own questions | `EDIT_OTHERS`: any | Any | Acting |
| Return / pass QC | No | `QC` | Yes | Acting |
| Approve (and return from QC_PASSED) | No | `APPROVE` | Yes | Acting |
| Publish (and return from APPROVED) | No | `PUBLISH` | Yes | Acting |
| **Read** a question that is IN_REVIEW or later, and the bank | **Yes, every member** | | Yes | Acting |
| Read a DRAFT or CHANGES_REQUESTED question | Own | `EDIT_OTHERS`: any | Any | Acting |
| Archive / restore (any state) | Own | | Any (`ARCHIVE_ANY_QUESTION`) | Acting |
| See the review queue and counts | Those holding at least one of QC, APPROVE, PUBLISH | | Yes | Acting |
| See a question's history | Anyone who can read the question | | Yes | Acting |

- **Reading after submit** is the one change to M3's privacy rule ("drafts are private"): submitted work is
  shared work, otherwise the bank would be empty for everyone but its authors. Drafts and returned questions
  stay private to their author, admins and `EDIT_OTHERS` (§17, decision 4).
- A grant is never read from the client: the `Principal` is reloaded on every request (B-10), so a removed
  member or a removed grant stops working on the next request. The API tells the screen which steps
  the signed-in person may take on a question (`allowed_steps`), so the web holds no rules.
- Every step writes an **audit event** and a `review_decisions` row. Autosaves still do not.

## 6. Notifications (I-01)

- Table `notifications` (user, kind, a small JSON `data` with the question code and ids, created, read time).
  A user reads only their own (a policy on the user, on top of the coaching's row-level security).
- M4 sends two kinds: **`REVIEW_RETURNED`** (to the author: the reasons and the note) and
  **`QUESTION_PUBLISHED`** (to the author). Taxonomy review, budget, job and prompt notices arrive with the
  milestones that create them (M5, M6).
- A bell in the app header shows the unread count; the page lists notifications, newest first, with
  *Mark as read* and *Mark all as read*. The count is read when a page loads and every 60 seconds, not pushed
  (no WebSockets in Phase 1). No emails (I-01).
- Notifications are created in the **same transaction** as the step that caused them, so a return never loses
  its message and a rolled-back step never sends one.

## 7. The bank: index, filters, search, duplicates

### 7.1 One derived table (ADR-0008, made concrete)

Content lives in JSON inside revisions, which cannot be filtered or counted quickly over a lakh of questions.
So `search` owns **`bank_index`: one row per master**, written by `questions` through `search.public` in the
same transaction as every save, checkpoint, step and archive, so it is never stale. It is **derived data**:
it can be dropped and rebuilt from the revisions with `python -m qbank.cli reindex-bank` (a one-off job per
coaching, needed after a bug fix or a change to what is indexed).

| Column group | Holds |
|---|---|
| Identity | master id, code, organization id, author, created and updated time |
| What the bank shows | the **bank version** (below), its state, whether archived, `has_published`, `has_open_correction` |
| Filters | class, subject, chapter, topic, primary concept (ids), concept ids (array), difficulty, Bloom, format, language, `is_pyq`, exam, year, has_solution, has_video |
| Text | `stem_text` (plain text of stem, options and solution; equations as their LaTeX), a `tsvector` of it, a **`content_hash`** for exact duplicates |

- **Which version a row shows:** the published version if there is one (a question being corrected still
  reads as published to everyone else), else the working one. The author sees their open correction from
  *My questions*.
- Each coaching only ever sees its own rows (`FORCE ROW LEVEL SECURITY`, ADR-0005, tested by the automatic
  isolation test from M3 that finds every table with an `organization_id`).
- Indexes: a b-tree per common filter combined with `organization_id`, a GIN on the concept array, a GIN on the
  `tsvector`, a GIN **trigram** index (`pg_trgm`) on `stem_text`, a unique index on `(organization_id, code)`.
  The final set is chosen from measurements (§12, T38), not guessed here.
- **Visibility is part of the query**, not a screen rule: a row of a DRAFT or CHANGES_REQUESTED version
  is returned only to its author, admins and `EDIT_OTHERS` holders. The same predicate serves list, count,
  search and duplicates, so a private draft can never leak through a count or a search hit.

### 7.2 Listing, filters, count, code (F-01, F-02)

- `GET /bank/questions?…filters…&limit=&cursor=` returns rows and `total` (the exact count with the same
  filters and visibility, so the number on the screen is the number of matches) in the style-guide format
  (cursor pages, stable order by update time then id). Filters combine with AND; several values of one filter
  with OR.
- `GET /bank/questions/by-code/{code}`: normalises the typed code as M3 already does (case, `O`/`0`, `I`/`L`
  confusion handled by Crockford) and answers 404 for another coaching's code, exactly like a missing one.
- The existing `GET /questions` ("my drafts") stays unchanged so the API contract does not break.

### 7.3 Free text and typos (F-03)

- Words are searched with PostgreSQL full text, configuration `simple` (no stemmer exists for the Indian
  languages; it still matches whole words in Hindi, Gujarati and the rest), through `websearch_to_tsquery`, so
  a user's text can never become query syntax.
- A search that finds few matches falls back to **trigram similarity** (`pg_trgm`) so "acceleratoin" still
  finds "acceleration". Results are ranked: exact words first, then close matches. Search returns at most the
  top 100 ("narrow your search"); there are no deep pages for a ranked list.
- The text is capped at 200 characters, rate-limited per user, and runs under a statement timeout so one bad
  query cannot hold the database.
- **Performance (the exit criterion):** a script creates **100,000 synthetic questions** directly in the
  database (made-up physics-like text, never real coaching content, never committed as data) and k6 scripts
  (K-08) measure list, filter+count, code lookup and search with several users at once. Proposed targets,
  for you to confirm or change (§17, decision 7): **p95 under 300 ms** for list, filter and count and **under
  800 ms** for search, on your PC with 5 simultaneous users. The measured numbers are written into the repo.
  If a target fails, the fix (index, query, or moving search to a dedicated engine) is a decision for you, as
  ADR-0008 already says.

### 7.4 Duplicate check (D-16, P1 part)

- **Exact:** the same `content_hash`, a hash of the question's meaning-bearing content after normalising
  whitespace, letter case in prose, and Unicode form. **Equations are compared as written** (a changed
  symbol, power or sign is a different question, because case and symbols matter in LaTeX), and options,
  answer and format are part of the hash. So "same stem, different answer" is not exact.
- **Near:** trigram similarity of `stem_text` above a threshold, with candidates fetched through the trigram
  index first (at most 20, same coaching only). The threshold is set from a small labelled sample once, and
  written down with the sample; we claim no accuracy beyond that.
- `GET /questions/{id}/duplicates` lists candidates (code, state, similarity, the same-text part) for the
  review revision, or for the working text of a draft. The screen shows the two side by side.
- The human decides: `POST /questions/{id}/duplicates/decisions` with `NOT_DUPLICATE` or `DUPLICATE_OF` (the other
  master) and a note, stored in `duplicate_decisions` with the revision it was made for. **An exact match with
  no decision blocks Pass QC** (`QC_BLOCKED_DUPLICATE`); a near match only informs. A `DUPLICATE_OF`
  decision means the author archives their copy; nothing merges or deletes automatically, and the other
  question is never changed. (Attaching a *source* to the existing question is M6, when sources exist.)
- Never searches another coaching, even when a code exists in both (the policy's first rule).

## 8. Diff and history (E-08, E-09)

- **Diff** (`GET /questions/{id}/diff?from=<revision>&to=<revision>`): both revisions must belong to this
  question (any version of it). The server compares them field by field (format, stem blocks, each option,
  answer, solution, each label) and returns a list of changes. Changed prose carries **word-level segments**
  (`equal` / `insert` / `delete`), equations and pictures count as single items, so an edited equation shows
  as *removed old / added new*. The web draws segments as text with marks; no content is ever turned into
  HTML. Default pair: the published version against the open correction.
- **History** (`GET /questions/{id}/history`): one timeline merging checkpoints, review decisions (submit,
  return with reasons and note, pass QC, approve, publish, withdraw), archive and restore, and the start of
  a correction, each with who and when. It is read from the question's own tables, so any member who can read
  the question sees it; the coaching-wide audit log stays for admins (I-03).

## 9. Database (migrations 0026 onwards)

All new tables carry `organization_id`, `FORCE ROW LEVEL SECURITY` with the tenant policy, composite foreign
keys (ADR-0005), and are covered by the automatic isolation test. Numbers are taken when each PR is written
(another track may add migrations in between); each is additive and safe to apply on a running system.

| Step | Change |
|---|---|
| Workflow | `question_versions` gains `state`, `flow_revision` (the ETag counter), `review_revision_id` (the frozen revision under review), `state_changed_at`; `question_masters` gains `published_version_id`. Existing M3 rows become `DRAFT`. Trigger: only the allowed state pairs; a PUBLISHED version and its revisions never change. `review_decisions` (append-only: version, revision, step, actor, reasons, note, checklist result, time) and `published_versions` (label snapshot, publisher, time) |
| Bank index | `bank_index`, the `pg_trgm` extension, the indexes; backfilled by the reindex command, not by SQL |
| Duplicates | `duplicate_decisions` (append-only: version, revision, other master, decision, note, actor) |
| Notifications | `notifications` (policy: own rows only) |

## 10. API (all under `/api/v1`)

| Method & path | Purpose |
|---|---|
| `POST /questions/{id}/submit` (`If-Match: "rev-N"`) · `/withdraw` · `/return` (`{reasons, note}`) · `/pass-qc` · `/approve` · `/publish` · `/start-correction` (these last six with `If-Match: "flow-N"`) | The steps; each answers with the question view, which now carries `state`, `flow_etag`, `allowed_steps`, `version_number`, `review_revision_id` |
| `GET /review/queue?state=&subject_id=&chapter_id=&author_id=&language=&older_than_days=&limit=&cursor=` · `GET /review/queue/counts` | The shared queue and the number waiting at each step |
| `GET /questions/{id}/history` · `GET /questions/{id}/diff?from=&to=` | Timeline and before/after |
| `GET /bank/questions` (filters, `q`, `total`) · `GET /bank/questions/by-code/{code}` | The bank |
| `GET /questions/{id}/duplicates` · `POST /questions/{id}/duplicates/decisions` | Duplicate check |
| `GET /notifications?unread=` · `GET /notifications/unread-count` · `POST /notifications/{id}/read` · `POST /notifications/read-all` | Notifications |

New error codes (added to `error-codes.md` in the PR that introduces each): `WORKFLOW_STEP_INVALID` (409),
`QUESTION_NOT_EDITABLE` (409), `CORRECTION_ALREADY_OPEN` (409), `PUBLICATION_CHECKLIST_FAILED` (422, with the
findings), `RETURN_REASON_REQUIRED` (422), `QC_BLOCKED_DUPLICATE` (409). Stale requests reuse `REVISION_STALE`
(412) and `IF_MATCH_REQUIRED` (428).

## 11. Web

| Screen | Content |
|---|---|
| Bank (the Questions page, widened) | Search box and code box; filter panel (all labels, state, format, language, PYQ, has-solution, has-video, author, archived); live count; rows with code, format, a stem snippet, state badge, labels, updated time; "Only mine" |
| Question page | State badge and an **action bar** showing only the steps the API allows; read-only editor with **Withdraw to edit** when in review; **Return** dialog (reasons + note); the Findings panel is titled **Publication checklist** once submitted; tabs **Edit · Preview · Compare · History**; a **Possible duplicates** panel |
| Review queue | Tabs *Waiting for QC · Waiting for approval · Waiting to publish · Returned to me* with counts and the E-05 filters; each row opens the question |
| Compare | Two pickers (revisions or versions) and the before/after view |
| Notifications | Bell with unread count in the header; list page |

The browser holds no rules: allowed steps, findings, visibility and counts all come from the API.

## 12. Tests that prove M4

| # | Test | Type |
|---|---|---|
| T33 | **State machine:** every state × every step × (no grant, each grant, admin, platform admin acting): allowed exactly as §4.1/§5; also the database trigger refuses a skipped step written directly | unit table + integration |
| T34 | **Stale approvals:** edit-after-QC needs a withdraw; resubmit gives a new review revision; old decisions cannot authorise it; two reviewers racing, one gets 412; a missing `If-Match` gets 428; a request naming another coaching's question gets 404 | integration + api |
| T35 | **Published is immutable:** UPDATE/DELETE of a published version or its revisions fails even as the table owner; correction makes version 2 while version 1 still reads the same; one open correction only; label snapshot survives a rename | integration |
| T36 | **Checklist:** each missing publication item blocks Pass QC, Approve and Publish; the check is repeated at publish after an answer limit or a catalogue change; warnings do not block | integration |
| T37 | **Visibility:** drafts and returned questions are invisible to other faculty in list, count, search, duplicates, history and by-code; visible after submit; removed member sees nothing | api |
| T38 | **Search and lists:** filters and `total` agree with a plain count; typo and Hindi fixtures; code lookup forms; hostile search text is inert; the 1-lakh fixture timings (K-08) are recorded | integration + k6 |
| T39 | **Duplicates:** exact (same), near (typo), not exact (a changed equation or answer), never another coaching's, exact blocks Pass QC until decided | integration |
| T40 | **Diff and history:** unit tests (including Hypothesis) that diff of equal revisions is empty and applying changes round-trips; history lists every step in order | unit + api |
| T41 | **Notifications:** return and publish send one each, in the same transaction; a user reads only their own; rolled-back steps send nothing | integration |
| T42 | **Browser journey:** faculty writes and submits; a QC person returns it with reasons; faculty fixes and resubmits; QC, approval and publish; the bank finds it by words (with a typo) and by code; a correction becomes version 2 and the old text stays; two tabs racing on one step | e2e |
| T30 | Isolation for every new table: **already automatic** (`test_every_tenant_table_is_isolated.py`), so a table that forgets row-level security fails CI | integration |

## 13. Before the first real use (the "first real use" checklist)

M4 is when real questions may be typed. These do not need new product features, but they must be true first:

| Item | State | Who |
|---|---|---|
| K-16 real scheduled backups, **including the `assetdata` picture volume**, and one real restore tested | Not started | **You choose the destination** (cloud bucket, cloud drive or an external disk kept elsewhere) |
| K-06 monitoring (errors, metrics, traces) | Built | Done |
| K-07 migration safety linter (squawk) in CI | Planned, small PR | Claude |
| K-08 k6 load scripts and the recorded 1-lakh timings | Inside M4 (§7.3) | Claude |
| Real content is entered only through the app, never committed, never in a test | Rule in AGENTS.md | Everyone |

## 14. Work plan (pull requests)

Each PR is one requirement, about 400 changed lines at most, with its own tests and docs.

| PR | Content |
|---|---|
| 1 | This design note + ADR-0020 (docs only). ADR-0008 is accepted in PR 4e, when the index is built |
| 4a-1 | The pure state machine (`domain/workflow.py`), reasons list, permission actions for the steps, T33 unit table. No database yet |
| 4a-2 | Migration (state, flow ETag, review revision, `review_decisions`, triggers); submit and withdraw; saves refused when not editable; `allowed_steps` in the question view; T34 part 1 |
| 4a-3 | Return, pass QC, approve with the checklist; audit; T34, T36 |
| 4a-4 | Publish, label snapshot, immutability trigger tests, start correction (version 2); T35 |
| 4b | `notifications` module (migration, routes) and the two kinds from 4a-3/4a-4; T41 |
| 4c | Review queue and counts (`review` module routes); visibility predicate; T37 part 1 |
| 4d | History and diff (backend, unit tests); T40 |
| 4e | `search` module: `bank_index` (migration), index writes from `questions`, `reindex-bank`, list + filters + count + by-code; T37, T38 part 1 |
| 4f | Free text and typo search; the 100,000-question generator; k6 scripts; recorded timings (K-08); T38 |
| 4g | Duplicate check (exact + near) and decisions; T39 |
| 4h | Web: workflow action bar, read-only editor, return dialog, publication checklist wording; e2e part 1 |
| 4i | Web: review queue and notifications bell and page |
| 4j | Web: bank screen (filters, count, search, code box) |
| 4k | Web: compare, history and duplicates panel |
| 5 | M4 demo notes and exit checks: `docs/operations/m4-demo.md`, the T42 journey, timings table |

K-07 (squawk) goes in as its own small PR when you say so, before 4a-2 if possible (so the new migrations are
checked). The order can change if a PR grows; split rather than stretch.

## 15. Security and safety (what could go wrong)

| Risk | Control |
|---|---|
| Someone publishes something that skipped review | One pure state machine, repeated by a database trigger; the publish step needs the grant, an APPROVED state and a passing checklist computed on the frozen revision |
| A reviewer approves text the author has since changed | The review acts on the frozen revision only; edits need a withdraw; every step needs the current workflow ETag |
| Two reviewers act at once | Row lock plus ETag; the loser gets 412 |
| Published text changes later | Trigger even for the table owner; no DELETE right; labels snapshotted |
| A draft leaks through search, count, duplicates or history | One visibility predicate in the query itself; tests probe every read path as another faculty |
| Another coaching's question appears in a search or duplicate list | Row-level security plus the coaching filter; code lookup of a foreign code is 404 |
| Search text turns into query syntax or runs long | `websearch_to_tsquery` only, parameters only (no string-built SQL), length cap, rate limit, statement timeout |
| Notes and reasons run script in a browser | Plain text rendered as text; never HTML; the renderer is not used for notes |
| A reviewer or admin edits history | `review_decisions`, `duplicate_decisions` and `published_versions` are append-only (no UPDATE or DELETE right); audit events are written with each step |
| The index disagrees with the content | Written in the same transaction as every change; a test compares index and content for each step; `reindex-bank` repairs it |
| One slow filter blocks the database at a lakh of rows | Measured on the 100,000-question fixture before M4 is closed; failing numbers are escalated to you (ADR-0008) |

New dependencies: none expected (`pg_trgm` is a PostgreSQL extension that ships with PostgreSQL; it is also
available on the managed PostgreSQL services considered for M7). k6 is a test tool run in a container, not a
runtime dependency.

## 16. Out of scope for M4

- AI tagging, translation, solving, verification and prompts (M5); the "source updated" flag (D-13, M5).
- Uploading papers, sources attached to an existing question, side-by-side extraction review (M6).
- "Reviewer must differ from the author" (E-03, P2); bulk submit and bulk edit (D-17, P2); comments (D-18, P3);
  saved filters (F-05, P3); find-similar by meaning (F-04, P2); a separate review of passages.
- Emails, push messages and WebSockets; assigning a question to one reviewer (the queue is shared, no lock).
- Exporting a bank, student apps, tests and papers.

## 17. Decisions for the owner

1. **Approve this note** (merge PR 1), or ask for changes.
2. **Editing during review needs an explicit Withdraw** (§4.2) instead of a silent return to DRAFT on the first
   keystroke. Same result as the spec, safer with autosave. I recommend yes.
3. **A holder of the Approve grant may return a question from QC_PASSED, and a holder of Publish from
   APPROVED** (§4.1), not only the QC person from IN_REVIEW. Otherwise an error found late has no way back
   except a withdraw by the author. I recommend yes.
4. **Submitted questions are readable by every member** of the coaching (§5); drafts and returned ones stay
   private. Needed for a shared bank. I recommend yes.
5. **Passages are reviewed together with their children**, with no separate workflow in M4 (§4.6). I recommend
   yes; a passage review can come later if you find you need it.
6. **Duplicates:** an exact copy blocks Pass QC until a person records a decision; a near copy only informs;
   nothing merges automatically (§7.4). I recommend yes.
7. **Search targets** (§7.3): p95 under 300 ms for list, filter and count and under 800 ms for search, on your
   PC with 5 users and 100,000 questions. Say if you want other numbers.
8. **Return reasons** (appendix): edit the wording or the list.
9. **Notifications:** only "returned" and "published" in M4, read on page load and every 60 seconds (§6).
   I recommend yes.
10. **Corrections are in M4** (§4.5): a published question can be corrected as version 2 of the same code.
    The spec needs it for "published versions immutable" to be usable. I recommend yes.
11. **Real use starts when M4 is done**, provided the §13 items are true. In particular **choose the K-16 backup
    destination** (it must include the picture volume). If you prefer to wait until AI help (M5) before real
    questions, say so and the checklist moves with it.

## Appendix: draft reasons for returning a question (for owner approval)

| Code | Shown to the author as |
|---|---|
| `ANSWER_WRONG` | The answer is wrong or does not match the question |
| `STATEMENT_UNCLEAR` | The question text is unclear, incomplete or ambiguous |
| `OPTIONS_FLAWED` | An option is wrong, repeated, or gives the answer away |
| `SOLUTION_WRONG` | The solution is wrong or skips steps |
| `LABELS_WRONG` | Class, subject, chapter, topic or concept is wrong |
| `DIFFICULTY_OR_BLOOM_WRONG` | The difficulty or Bloom level does not fit |
| `DUPLICATE` | This looks like a copy of another question |
| `FORMATTING` | Equations, pictures or layout need fixing |
| `OTHER` | Something else (explained in the note) |
