# M6 demo: check document upload and question extraction yourself

M6 ("Document ingestion v1") is done when the [phase plan](../product/02-phase-plan.md) exit criteria hold:
**extraction quality is measured on your sample pages, and cancel/retry never loses or duplicates work.** This page
shows how to see the plumbing on your PC with no provider key, then how to measure real quality on your own papers.
The design is in the [M6 design note](../architecture/m6-design-note.md), [ADR-0024](../architecture/adr/0024-document-worker-sandbox.md)
and the [uploads threat model](../architecture/threat-model-uploads.md).

Use made-up files and `@example.com` emails. Never upload real coaching content while testing.

## 0. Set up

As for the [M5 demo](./m5-demo.md#0-choose-how-to-try-it), option A: `AI_KEYS_MASTER_KEY` and `AI_DEMO_PROVIDER=true` in `.env`,
then `docker compose up --build -d`. Two things are new in this stack:

- **`ingest-worker`** is a separate container that opens uploaded documents. It has no network, a read-only
  filesystem, almost no privileges and a small memory limit, and its own database login that can reach only the
  upload tables. A hostile document can at worst crash that one container. Check with
  `docker compose ps` (it should be running) and `docker compose logs ingest-worker`.
- **`INGEST_DB_PASSWORD`** (in `.env.example`) is that login's password; the default is for local use only.

Sign in as the Owner of a test coaching and invite one faculty member, **Anita** (as in the [M2 demo](./m2-demo.md)).

## 1. Choose the model that reads pages (Owner)

Menu → **AI** → store any key under **OpenAI** (the demo accepts any text), **Refresh the list**, tick **Offer Demo large**.
Under **Reading uploaded documents**, choose *Demo large* and **Save**: "Documents are read with this model from now on."

A model can only be chosen if an admin has turned it on **and** it is known to read pictures. The demo's *large* model does;
with a real provider, tick **This model reads pictures** on its row (the catalogue does not always say).

## 2. Upload (Anita) (G-01, G-09)

Menu → **Uploads**. Drop a file on the box, or choose files. PDF, Word (.docx), JPEG, PNG, WebP and HEIC are accepted; the
**type is decided from the file's first bytes, never its name**.

| Step | Expected |
|---|---|
| Upload a small PDF (any 1 to 3 page PDF; a printout of a few made-up questions is ideal) | "sent", then the row shows *Waiting*, then *Pages ready* with a page count, with no reload |
| Rename any non-document (a `.txt`, or a program) to `paper.pdf` and upload it | A plain sentence: "This is not a PDF, Word, or picture file." Nothing is stored |
| Upload the same PDF again | Accepted, and the row says it is the same file as an earlier one (nothing is deleted or merged) |
| Open the document | Each page as a picture; a Word file shows text pages with its pictures and an *equation kept as text* note where a formula was |
| **Download the original** | The exact bytes you uploaded, always as an attachment (never opened in the browser) |

Limits, so one person cannot clog the worker: 50 MB per PDF or Word file, 10 MB per picture, 200 pages, a number of uploads per
10 minutes and a number of documents in progress per person. A page that is too big, a picture of tens of millions of pixels, a
zip-bomb Word file or a PDF that will not open each **fail alone with a reason**; they never stop other files or the worker.

## 3. Read the questions (G-03, G-04, G-06)

On the document, press **Read the questions**. Each page costs one AI call against Anita's budget ([M5 demo §3](./m5-demo.md)); nothing
is called if she has no budget left.

| Step | Expected |
|---|---|
| Watch the page | *Reading…* then "N found, N waiting". Anita gets an in-app notice "Your document has been read" that links back here |
| Press **Cancel** while it is reading | It stops before the next page; what was already read is kept |
| Press **Read again** later | A new run; earlier candidates and decisions stay on record |

The demo provider invents one made-up question per page, from the page's own text. A real model reads the page picture: stem,
options, formulas as `\( … \)`, and **only an answer that is printed on the page** (never a guess). An answer printed with
more decimals than the answer rules allow is flagged, **never rounded**.

## 4. Review (the screen where a person decides)

Press **Review the questions**. The printed page is on the left, the question the AI read in the middle (the same editor as a normal
question), checks and *Already in the bank?* on the right, and a list of all questions at the bottom right.

| Key | Does |
|---|---|
| `j` / `k` | Next / previous question |
| `n` | Next question still waiting |
| `a` | **Create question** |
| `r` | Go to the reason box to reject |
| `s` | **Same as an existing question** (pick from the duplicates shown) |

Letters typed in a box are typing, never a shortcut. Nothing is automatic: **AI only proposes; a person decides.**

| Step | Expected |
|---|---|
| Edit the question text, then **Save changes** | Checked again; the model's own reading stays on record underneath (it is never overwritten) |
| **Create question** | "Created as a draft question": a new **draft** of Anita's, linked back to its page. It still goes through submit and review like any other (M4); nothing is published |
| **Same as an existing question** | Nothing new is made; the source page is attached |
| **Reject** with a reason | Final, with the reason on record. Deciding the same question twice is refused |

## 5. Cancel, retry and restarts never lose or duplicate work (exit criterion)

- Stop the normal worker mid-reading (`docker compose stop worker`, then `docker compose start worker`): the reading resumes where
  it was. A page already read is not read, charged or written twice.
- Stop the `ingest-worker` while a file is being turned into pages and start it again: the file finishes, with no duplicate pages.
- **Cancel** a document: pages and candidates already made are kept; a cancelled document can be retried.

## 6. Measure extraction quality on your own papers (G-11, K-14) <a id="measure"></a>

CI can only prove the *plumbing* with a made-up model. **How good a real model is on real papers is measured by you, on your
samples**, and the result is reported as it is.

1. Upload 3 to 5 real papers of different kinds: printed, scanned, a phone photo, one with handwriting. Read them with a real
   model (turn the demo provider off, store a real key, see [ai-keys.md](./ai-keys.md)).
2. Review the questions properly and **Create question** for each one you would keep (fix mistakes first).
3. As an admin, collect them into a **golden set** (an answer key). There is no screen for this yet; use the API (it is documented at
   `http://localhost:8000/docs` under *ingestion*): `POST /api/v1/ingest/golden-sets` with `{"name": "Term 1"}`, then
   `POST /api/v1/ingest/golden-sets/{id}/cases` with `{"candidate_id": …}` for each accepted question.
   Only an accepted question can join the key, and its content is frozen as you finished it.
4. Score a model against it (this calls the real provider with your stored key and costs a small amount):

```bash
docker compose run --rm -e MIGRATION_DATABASE_URL=... migrate \
  qbank ingest-measure --organization <coaching id> --set "Term 1" --provider openai --model <model id>
```

   (`MIGRATION_DATABASE_URL` is the table-owner connection, as for `qbank ai-smoke`.) It prints, for the questions in the key: how
   many the model found, how many were **entirely right**, the share right in type, text, options and answer separately, how many
   questions it read that are not in the key, pages it could not read, and tokens used. Words are compared ignoring case and
   spacing; **a changed digit counts as wrong**.
5. **Before changing the prompt or switching the model, run it, change, and run it again.** A prompt or model change must show its
   score (K-14); put both numbers in the pull request.

## 7. What M6 does not do yet (honest list)

- **Economy (half price, slow) for whole files** is not built: a reading is always *Now*. The design allows it later.
- **Golden sets have no screen** (API and command only), and an extraction's cost is visible in **AI usage** per run but not summarised per file.
- **Handwriting (G-05) is best effort:** it follows the same path and carries a *handwritten* warning; measure it on your own samples.
- **Real-model quality is unmeasured until you do step 6.** Do not trust an extraction for a paper you have not reviewed.
- Originals are kept; there is no deletion screen (Phase 1).
