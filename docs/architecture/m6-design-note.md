# M6 Design Note: Document ingestion v1

> Status: **Approved by the owner on 2026-11-28.** D1 = option A (read Word files directly); D2, D3 and D5 follow the
> recommendations below; D4 (sample files) is asked again at 6j. Milestone M6 of Phase 1
> ([phase plan](../product/02-phase-plan.md)).
> Requirements: G-01, G-03, G-04, G-05 (best effort), G-06, G-09, G-11, D-16 (duplicate check on candidates),
> I-01 (in-app notices) · Hardening: **K-17** (uploads threat model and a separate low-resource parsing worker; the
> [threat model](./threat-model-uploads.md) is drafted with this note), K-14 (evaluation harness applies to
> extraction prompts too)
> · ADRs 0005, 0007, 0009, 0012, 0016, 0020, 0023 · **ADR-0024 (new, accepted): untrusted documents are
> parsed only in a sandboxed worker**
> Not in M6 (Phase 2): separate answer-key and solution files paired to a paper (G-07), adaptive layout patterns
> (G-08), original deletion and storage dashboard (G-10), legacy `.DOC` (G-02), diagram generation, semantic
> duplicates.

## 1. Goal

A coaching can upload its existing question papers (PDF, Word, photos) and turn them into reviewed questions
without retyping. The upload is kept as an **original**; the pages are read by AI; every question found becomes a
**candidate** next to a picture of where it came from; a person fixes it on a side-by-side screen and creates a
real question from it. From there the normal workflow (M4) applies: nothing is ever published by an upload or by
AI.

## 2. What you will be able to do at the end of M6

1. Drag in one or many files (PDF, DOCX, JPEG, PNG, WebP, HEIC) and keep working. Each file shows progress and
   can be cancelled or retried.
2. See, per file, its pages and how many candidates were found, what is still being read, and what could not be
   read (with the reason).
3. Open a file in the **extraction review** screen: the original page on the left, the extracted question in
   the middle (editable, same editor parts as M3), metadata and possible duplicates on the right; keyboard
   shortcuts to go to the next candidate, accept, reject.
4. For each candidate choose **Create question** (a new draft, linked back to its page and region), **Same as an
   existing question** (nothing new is made, the source is attached), or **Reject** (with a reason).
5. Open the original at any time (G-09). Originals are never deleted in Phase 1.
6. As an admin, see what an extraction cost (AI usage, per file) and set the model used for extraction.
7. As the owner, mark reviewed results as the **golden set** and run a measurement of extraction quality against it
   before and after any change to the prompt or model (G-11).

## 3. Decisions for you (change them by editing this note)

| # | Question | Recommendation | Why it matters |
|---|---|---|---|
| D1 | **Word files.** Option A: read the `.docx` directly (text, tables, embedded pictures); equations that are not plain text are kept as a picture and flagged. Option B: convert to PDF with LibreOffice in the sandbox and treat it like a PDF | **A for Phase 1**, B in Phase 2 together with `.DOC` (G-02) | B reads equations and layout better but adds a large program that parses untrusted files. A is smaller and safer; its weakness is equations written in Word's equation editor |
| D2 | **Picture formats.** HEIC (iPhone photos) needs one extra native library | **Include HEIC** | Faculty photograph pages with phones |
| D3 | **Where the sandboxed worker runs.** A separate container with no network, a read-only filesystem, a memory and CPU cap and a time limit per file | **Yes, from M6**, as another service in `compose.yaml`; the cloud equivalent is chosen in M7 | K-17 asks for it; a bug in a PDF library must not reach the database or other coachings |
| D4 | **Sample files for the golden set (G-11).** You upload real papers during M6 | You choose 3 to 5 papers: printed, scanned, a phone photo, a handwritten page | Without them extraction quality is unmeasured; the plan says "measured on your sample pages" |
| D5 | **Extraction model.** A vision-capable model chosen in Admin, AI like the other operations | Start with one model; Economy (half price) allowed for whole files | A page costs roughly one picture plus the text of the questions |

## 4. Modules and where the risk sits

```
services/api/src/qbank/modules/ingestion/        new module (public.py is its only door)
  sources/        uploads, originals, pages            (uses core/storage, assets rules)
  render/         PDF/DOCX/image → page pictures + text   RUNS ONLY IN THE SANDBOX WORKER
  extract/        page pictures + text → candidates       runs in the normal worker, via the AI orchestrator
  candidates/     review actions, links to questions
services/api/src/qbank/ingest_worker.py          entry point of the sandbox worker (like worker.py)
```

Only `render/` ever opens an untrusted document. It is imported by `ingest_worker.py` and nothing else (an
import-linter contract enforces it, so the API process cannot parse a document even by mistake). The API process
stores the bytes and starts jobs; the normal worker talks to AI providers; the sandbox worker has **no network
and no database role that can read other coachings** (§8).

## 5. Data (migrations 0043 onwards; each table has `organization_id`, forced RLS, composite tenant keys)

| Table | Holds |
|---|---|
| `ingest_files` | One upload: original file name, kind, size, SHA-256, storage key of the original, uploader, state, page count, error code. Never changed after upload except state/counters |
| `ingest_pages` | One page: file, number, storage keys of the page picture (and thumbnail), extracted text if any (for selectable-text PDFs and Word), state |
| `ingest_runs` | One extraction of one file (a retry makes a new run): model, prompt version, mode (Now/Economy), state, counts, cost ledger link |
| `ingest_candidates` | One question found: run, page, region box (page fractions), **raw evidence** (what the model read), typed content (M3 format), warnings (overprecision, unreadable, handwritten), a labels proposal, state `NEW → ACCEPTED / REJECTED / DUPLICATE`, the question it became |
| `ingest_candidate_events` | Append-only: who did what to a candidate, when (I-03 style) |
| `golden_sets`, `golden_cases` | A named set; each case is a reviewed candidate frozen as the expected result |

An upload and its pages are immutable evidence: correcting a candidate never edits the picture or the model's raw
reading, only the candidate's editable content, so what the AI said is always inspectable.

## 6. Jobs and states

```text
file:   UPLOADED → RENDERING → READY → (EXTRACTING) → DONE | PARTIAL | FAILED | CANCELLED
job 1   ingest.render   sandbox worker   file → pages (pictures, text), one job per file
job 2   ingest.extract  normal worker    one job per page group; calls the orchestrator's vision operation
job 3   ingest.collect  normal worker    Economy only, as in M5
```

- **Durable and restart-safe** (N-05, ADR-0007): all state is in PostgreSQL; a job is a row. A page is rendered at
  most once (output keyed by file hash and page number, so a retry overwrites with identical bytes); a candidate has
  a unique key `(run, page, ordinal)` so a retry **never duplicates** one.
- **Partial results are kept**: if page 7 fails, pages 1 to 6 and 8 onward stay; the file is `PARTIAL` and page 7
  says why. Retry re-runs only what failed.
- **Cancel** (own upload, or an admin): future pages are not started, running ones finish or are abandoned, nothing
  already extracted is thrown away. A result arriving after cancel is stored but never creates anything.
- **Limits:** 50 MB per document, 10 MB per image (G-01), at most 200 pages per file, at most 20 files in flight per
  coaching, 2 renders at once in the sandbox. A document over a limit is refused with a plain message before anything
  is read.

## 7. Extraction (the AI part; H-15, ADR-0009)

- A new operation `EXTRACT_QUESTIONS` goes through the same orchestrator path as tag, solve, verify and translate:
  permission, budget reservation, prompt version, locked schema, domain checks, ledger.
- **Vision input.** The provider interface gains an optional list of images on `StructuredRequest`. Each adapter
  maps it to its provider's picture input; a model whose catalogue entry says it cannot read pictures is not
  offered for this operation.
- **Output is untrusted** (AGENTS.md). The model returns, per page, a list of questions with their type, stem,
  options, answer if printed, region box and a confidence note. Each goes through the **same validators as a
  person's save** (M3). Text from a page is data between markers; an instruction inside a scanned page is ignored
  and tested (T53 style).
- **Coverage is explicit.** Every region of a page is either a candidate, marked *unreadable*, or marked *not a
  question* with a reason. A page with nothing found is shown as such, never silently skipped.
- **Handwriting (G-05) is best effort:** same path, `handwritten` warning, lower trust; quality is measured in
  Phase 2.
- **Numbers keep their precision.** An answer written with more digits than the answer rules allow is flagged,
  never rounded (spec rule).
- **Metadata:** the same tagging operation fills labels for each candidate once, only for accepted ones, so cost
  is not spent on rejected questions.

## 8. The sandboxed worker (K-17, ADR-0024)

A separate container started from the same image with a different command:

| Control | Setting |
|---|---|
| Network | none (no route out), so a parser bug cannot call anywhere |
| Filesystem | read-only root; one small writable scratch folder, emptied after every file |
| Resources | memory and CPU capped; a process-count cap; a wall-clock limit per file (kill, then mark the file `FAILED: took too long`) |
| Database | its own role that may only claim `ingest.render` jobs and write `ingest_pages` for the job's own coaching; it cannot read questions, keys, users or any other table |
| Files | it reads one original and writes page pictures through storage keys derived from the job, never from the file's content |
| User | non-root, no extra privileges |

Parsers run only here. See the [threat model](./threat-model-uploads.md) for each attack and the control for it.

## 9. Who may do what

| Action | Faculty | Admin / Owner | Platform admin |
|---|---|---|---|
| Upload files, see their own uploads, cancel or retry them | Yes | Yes (everyone's) | Acting |
| Review candidates of their own uploads, create questions | Yes (needs the same right to author as M3) | Yes | Acting |
| Review others' uploads | If granted *edit others' questions* | Yes | Acting |
| Choose the extraction model and prompt | No | Yes (grant `MANAGE_AI_PROMPTS` for the prompt) | Acting |
| Mark the golden set, run a measurement | No | Yes | Acting |

As everywhere, the coaching, role and grants are resolved on the server on every request; a removed member loses
access at once (B-10), and a result that arrives later is applied only if the person may still do it.

## 10. Web

New pages through `/api/v1` with the generated client, no rules in the web: **Uploads** (list, drop zone,
progress, cancel, retry), **Upload detail** (pages, candidate counts, cost, open original), **Extraction review**
(three panels, keyboard shortcuts), **Admin → AI** gains the extraction model. Question detail shows "created from
file X, page N" with a link to the page.

## 11. Tests that prove M6 (continuing the T-numbers of M5)

| # | Test | Type |
|---|---|---|
| T56 | **Upload rules:** type by content not by name, size limits, page limit, too many files in flight, rate limit; refused before anything is read | integration |
| T57 | **Isolation:** every new table automatic in the tenant-isolation test; the sandbox role cannot read other tables or other coachings' files | integration |
| T58 | **Hostile files** (see the threat model): a zip bomb in a DOCX, a PDF with a huge page, a PDF with embedded scripts or launch actions, a 40-megapixel image, a corrupted HEIC, a file with a lying extension, path tricks inside a DOCX; each ends as a plain failure without hurting the worker | unit + integration |
| T59 | **Sandbox:** the worker's compose service has no network, a read-only filesystem and limits (checked from the compose file in CI); a render that exceeds its time is killed and the file marked failed | integration |
| T60 | **Restart safety:** kill the worker mid-file; the retry produces no duplicate pages or candidates; partial results survive; cancel keeps extracted work | integration |
| T61 | **Extraction through the orchestrator** with the fake provider: valid answers become candidates; invalid ones are stored as failed and create nothing; budget refusal; prompt injection inside a page's text is treated as data | integration |
| T62 | **Candidate actions:** create question, same-as-existing, reject; a created question carries its source; permissions; a stale candidate cannot be applied twice | integration |
| T63 | **Golden-set measurement:** the harness scores the fake provider on known cases in CI; a real-provider score is required before a prompt or model change merges (K-14) | integration |
| T64 | **Browser journey:** upload a small sample PDF, see it progress, review a candidate side by side with keyboard shortcuts, create a question, open the original | e2e with the demo provider |

**What cannot be tested in CI:** extraction quality on real papers. That is G-11 and needs your sample files. The
demo provider reads a built-in sample page, so the screens and the plumbing are tested; the quality of the real
models on real pages is measured by you on your own samples and reported honestly.

## 12. Hardening items due with M6

K-17 (this note and the threat model), K-14 applied to the extraction prompt, K-06 monitoring includes job and
render metrics (duration, failures, queue depth), K-16 backups now include the original files and page pictures (the
backup scripts already copy the storage folder; the restore drill gains a check that the files match).

## 13. Work plan (pull requests, each under about 400 changed lines of code)

| PR | What | Tests |
|---|---|---|
| 6a | ADR-0024, import-linter contract, sandbox worker service in compose (no network, limits), render job skeleton, worker claims only registered job types | T59 |
| 6b | `ingest_files`, upload endpoint (raw body like pictures), type by content, limits, rate limit, originals in storage, list and detail routes | T56, T57 |
| 6c | Render: images (Pillow, HEIC), PDF to pictures and text; page tables; progress and partial results | T58, T60 |
| 6d | Render: DOCX read directly (D1 option A) | T58 |
| 6e | Vision input on the provider interface and the four adapters; `supports_vision` honoured | adapter tests |
| 6f | `EXTRACT_QUESTIONS` operation, candidates table, coverage rules, extraction job and Economy variant | T61 |
| 6g | Candidate actions and links to questions; duplicate check on candidates | T62 |
| 6h | Web: Uploads and Upload detail | unit |
| 6i | Web: Extraction review screen with keyboard shortcuts | unit |
| 6j | Golden set and the measurement command; evaluation harness | T63 |
| 6k | M6 demo notes, T64 browser journey, review pass | T64 |

## 14. What I need from you before 6a starts

Approve this note (or change it), and answer D1 to D5. D4 can wait until 6j, but the earlier you upload real
sample pages, the earlier extraction can be tuned on them.
