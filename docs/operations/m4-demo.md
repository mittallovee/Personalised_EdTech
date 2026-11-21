# M4 demo: check review and the bank yourself

M4 ("Review & bank") is done when the [phase plan](../product/02-phase-plan.md) exit criteria hold:
**published versions are immutable, stale approvals are refused, and search stays quick on a 1-lakh
(100,000-question) bank.** This page shows how to see each of those on your PC, then walks through
everything M4 can do in about an hour. Setup is in the
[README](../../README.md#run-it-locally-windows-pc-with-docker-desktop); the design is in the
[M4 design note](../architecture/m4-design-note.md) and
[ADR-0020](../architecture/adr/0020-review-workflow-bound-to-a-frozen-revision.md).

Use made-up questions and `@example.com` emails. Never type real coaching content while testing.

## 0. Start fresh, and set up three people

```bash
docker compose up --build -d
```

Sign in as the Owner of a test coaching (see the [M2 demo](./m2-demo.md), steps 1 and 2, and the
[M3 demo](./m3-demo.md) for the syllabus you need first: a class, subject, chapter, topic and one
concept). Then, on **Users & grants**, invite two people and open each activation link in a **separate
browser** (or a private window), so each has their own sign-in:

| Person | Role | Grants |
|---|---|---|
| **Anita**, faculty | Faculty | none |
| **Kiran**, a reviewer | Faculty | **Quality check**, **Approve**, **Publish** (tick all three) |

The Owner and admins hold every grant already, so one person *can* take every step. Two people show
the rules better.

## 1. The steps of review (E-01, E-02, E-04, E-06, E-07)

A question is in one state at a time: **Draft → In review → QC passed → Approved → Published**, or
**Returned to the author** after a return. The buttons show only the steps the server allows.

| Step | Expected |
|---|---|
| As **Anita**: write a finished question (see M3), then press **Submit for review** | State **In review**. The editor is read-only: "This text is under review and cannot be edited. Withdraw it to make changes." The Findings panel is now titled **Publication checklist** |
| Try to submit a question that still has a **Mistake** | Refused with the reason; things still "to do" are allowed at this step, but not at QC, approval or publishing |
| As **Kiran**: menu → **Review** | The **Waiting for QC (1)** tab lists it, with its age. Anita has no Review item (no grant) |
| Open it, press **Return to the author** | A form needs at least one reason and a note ("What should the author fix?"); the button stays off until both are there |
| As **Anita**: the bell shows **Notifications 1 unread** | The notification says the question was returned, with the reasons and the note; opening it marks it read and opens the question, now **Returned to the author** and editable |
| Fix the text, **Submit for review** again | In review again. It is a **new frozen text**: Kiran's earlier return does not carry over |
| As **Kiran**: **Pass QC**, then **Approve**, then **Publish** | Each step moves the state. **Publish** asks first ("A published question never changes") |
| As **Anita**: the question is **Published** | Everyone in the coaching can now use it. The only button is **Start a correction** |

**Two tabs, one step.** As Kiran, open the same In-review question in two tabs. Press **Pass QC** in the
first. In the second (still showing "In review") press **Pass QC**: it is **refused** with "Reload", not
repeated. This is the stale-screen rule: every step names the version of the workflow it was looking at
(`If-Match`), so a decision made on an old screen is never applied.

## 2. A published question never changes (E-07; exit criterion)

| Step | Expected |
|---|---|
| On the published question press **Start a correction** and confirm | It becomes **version 2**, a **Draft** again. The published version 1 is untouched and is still what everyone else reads |
| Change the text of version 2 and let it save | Anyone else (Kiran) still sees the **old** text in the bank and by code, and **cannot read the draft at all** |
| Take version 2 through the same steps and publish it | Version 2 is now the one in use. Version 1's text is still in the history |

The database enforces this as well as the app: even a direct SQL `UPDATE` of a published version or its
saved text is refused by a trigger. (Tests: `test_question_publish.py`,
`test_question_workflow_database.py`.)

## 3. History and comparing two texts (E-08, E-09)

On a question with a few steps behind it, use the tabs on the question page:

| Step | Expected |
|---|---|
| **History** tab | Every step oldest first, with when and who ("you" or "a colleague"). A return lists its reasons and note |
| **Compare** tab | Two choices, **Older text** and **Newer text**, set to the two newest saved texts. Words added are underlined, words removed are struck through; an unchanged pair says "These two texts are the same." |
| Choose the same text in both | "These two texts are the same." |

Someone who may read only the published version never sees the steps of a private correction in the
history, and cannot compare against its text (the server answers as if it did not exist).

## 4. The bank: list, filters, counts, code, search (F-01, F-02, F-03)

Menu → **Questions**. Below *Start a new question* is the bank: every question **you may open**, the
most recently changed first, 50 at a time.

| Step | Expected |
|---|---|
| Look at the count line | "N questions" is exact. Drafts of other people are not in it or in the list |
| Pick **State: Published**, a subject, a chapter, a topic, a difficulty | The count and list follow each choice; chapter lists only that subject's chapters, and so on. **Clear** resets |
| Tick **Only mine**, **Has a solution**, **Past-year**, **Archived** | Each narrows the list; **Archived** shows the archive instead |
| Search for a word from a stem | The best matches, ranked. Quotes find a phrase; `-word` leaves a word out |
| Search again with a typo ("pendulm" for "pendulum") | The question is still found. A search waits for a short pause in your typing before it asks |
| **Open by code**: type the code in lower case with a dash in the middle | The question opens. An unknown code says "No question has that code." |

**Before any of this finds your existing questions, run the index rebuild once** (it fills the search
text, previews and duplicate keys of questions saved before M4; about 14 minutes per 100,000):

```bash
docker compose run --rm migrate qbank reindex-bank
```

See [bank-index.md](./bank-index.md). Questions saved after the upgrade are indexed as they are saved.

## 5. Possible duplicates (D-16)

On a question page the **Possible duplicates** panel lists questions of the same coaching with the same
content ("Same content") or very similar text ("Similar text (83%)"), only ones you may open and never
archived ones.

| Step | Expected |
|---|---|
| Make a second question with exactly the same stem, options and answer | The first question's panel lists it as **Same content** |
| Press **Not a duplicate**, write why, **Save decision** | "You decided: not a duplicate." The decision is for the text as it is now; a later edit of the question needs a new decision |
| (Reviewer) a **shared** (submitted or published) exact copy with no "not a duplicate" decision | **Pass QC is refused** (`QC_BLOCKED_DUPLICATE`), and the panel says which questions block it. Private drafts and archived questions never block |
| Press **This question copies it** | Records that it is a copy; it also blocks Pass QC while the other is shared. Nothing is merged or deleted |

## 6. Timings: the exit criterion for search

Measured on 2026-11-17 on the owner's PC, 100,000 made-up questions, five people at once for three
minutes (full method and the ten-person run in [load-tests.md](./load-tests.md)):

| Request | p95 | Target |
|---|---|---|
| List (50 rows and the exact total) | 131 ms | 300 ms |
| Filter and count | 119 ms | 300 ms |
| Lookup by code | 81 ms | 300 ms |
| Search (including typos) | 235 ms | 800 ms |
| Possible duplicates, near match (opened by a person, not on every list) | 60 to 270 ms | under the 5 s limit |

(p95 means 95 out of 100 requests were at least this fast.) All four targets are met. The limit is the
single API process: with ten people each request waits about twice as long, so repeat the test when
hosting gives us more processes (M7).

## How M4 is checked on every pull request

The same checks as before, plus the M4 tests (T33 to T42 in the design note):

| Test | Where it lives |
|---|---|
| T33 the state machine, every state and step and permission | `services/api/tests/unit/test_question_workflow.py`, `integration/test_question_review_steps.py`, `test_question_workflow_database.py` (the trigger refuses a skipped step) |
| T34 stale approvals, a missing `If-Match`, another coaching's question | `test_question_submit_withdraw.py`, `test_question_review_steps.py` |
| T35 published is immutable, corrections, label snapshot | `test_question_publish.py`, `test_question_workflow_database.py` |
| T36 the publication checklist | `test_question_review_steps.py`, `test_question_publish.py` |
| T37 who can read what | `test_question_history_diff.py`, `test_bank_search.py`, `test_duplicates.py`, `test_review_queue.py` |
| T38 filters, totals, search, hostile search text; the 1-lakh timings | `test_bank_search.py`, `test_bank_index.py`, `tests/unit/test_bank_text.py`; `infra/load/bank.js` (k6) |
| T39 duplicates and the QC block | `test_duplicates.py`, `test_duplicate_decisions.py`, `tests/unit/test_duplicate_key.py` |
| T40 diff and history | `tests/unit/test_question_diff.py` (Hypothesis), `test_question_history_diff.py` |
| T41 notifications | `test_notifications.py` |
| T30 isolation for every table | `test_every_tenant_table_is_isolated.py` (automatic for each new table) |
| T42 the browser journeys | `apps/e2e/tests/m4-exit.spec.ts` (the whole journey with three people: submit, return, fix, QC, approve, publish, search with a typo, by code, a correction, two tabs racing) and the screens' own specs: `workflow.spec.ts`, `review-queue.spec.ts`, `bank.spec.ts`, `compare.spec.ts` |

The browser tests run on GitHub on every pull request (the whole `docker compose` stack driven by Playwright); see
[apps/e2e/README.md](../../apps/e2e/README.md) to run them on your PC.

## What M4 does not have

- AI of any kind: tagging, translation, solving, checking (M5).
- Uploading a paper or book and extracting questions from it (M6).
- Comments on a question, bulk actions, and the setting "a reviewer must differ from the author" (later).
- Names in the history (it says "you" or "a colleague"); the default comparison of a published version
  with its open correction (the two newest saved texts are chosen instead).
- Real scheduled **off-site backups** (K-16): the tooling is built, but **you** still create the Cloudflare
  R2 bucket and key. Do that before entering real content ([offsite-backups.md](./offsite-backups.md)).

## If something goes wrong

| Symptom | Fix |
|---|---|
| The bank is empty, or search finds nothing, for questions you saved earlier | Run `qbank reindex-bank` once (section 4) |
| "Someone else changed this", or a step is refused with Reload | The screen was out of date (another tab or person moved it on). Press **Reload** |
| Pass QC is refused with a duplicate message | Open **Possible duplicates**, decide each listed question |
| A search says it took too long | It stopped at 5 seconds; add a word or a filter and try again |
| "The check took too long" in Possible duplicates | Press **Check again** |
| Anything else | `docker compose ps`, `docker compose logs --tail 100 api`, and send the output |
