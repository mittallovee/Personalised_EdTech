# ADR-0018: The syllabus import is parsed inside the API request, with added limits; documents go to a worker
- Status: **Accepted** (owner, by merging PR #56, 24 Oct 2026) · Date: 2026-10-24 · Requirements: K-10, K-10a, K-10b (C-03, T25) · Evidence: [threat model](../threat-model-import.md)
## Context
The Excel/CSV syllabus import parses an untrusted file inside the API process (a worker thread of the request). It
already has hard limits (5 MB, 20,000 rows, 40 columns, 20 MB unpacked, a streaming reader of our own, no formulas,
no entities). K-10 asks: keep that, or move parsing to a separate low-resource worker (ADR-0007 job queue)?
The [threat model](../threat-model-import.md) measured the worst allowed file at about **2.5 s of one core and
25 MB**, and found two gaps: **no limit on how often** an admin may upload or on how many parses run at once, and
**previews stored forever** (6 to 8 MB each). Only an owner or admin can upload, and the permission is checked
before the file is read.
## Decision
1. **Keep the syllabus import parsing in the API request.** The worst case is bounded and small, the uploader is a
   trusted, signed-in role, and moving it now would need things that do not exist yet: stored uploads (ADR-0012 is
   only a decision so far), a parse job, a "processing" state and polling in the screen.
2. **Add three controls before the import screen is built (2d-3):**
   - **K-10a:** a per-user limit on `POST /taxonomy/imports` (proposed: 10 per 10 minutes, with the existing
     sliding-window limiter) and **at most 2 parses at the same time** per process; beyond that an upload is
     refused at once with a clear message and `Retry-After`.
   - **K-10b:** retention of previews (proposed: at most 20 unapplied previews per coaching; stored rows of an
     unapplied preview dropped after 30 days; applied previews keep theirs). This changes "previews are never
     deleted" in the M3 design note for previews that were never applied; **the owner confirms**.
   - The attacks that a library stops but nothing tested (XML entities, external references, understated archive
     sizes) now have tests (done with this ADR).
3. **Untrusted documents are different.** Uploads of question papers, PDFs and images (M6, K-17) **must be
   parsed in a separate low-resource worker** from day one: they are larger, far less structured, and need OCR and
   third-party tools. When that worker exists, **move the syllabus import onto it**: `read_table` and
   `build_plan` are already pure functions, so the move is storing the bytes and calling them from a job.
4. **Reopen this decision** if the uploader set widens beyond owners and admins, the limits are raised, one parse
   exceeds about 5 s or 50 MB on the real host, or the API runs behind several processes without a shared limit.
## Consequences
+ The import screen can be built now, on the existing API, with no new moving parts.
+ A noisy admin can slow the API for a few seconds at a time but not hold it, and cannot fill the database.
+ The M6 worker is designed once, for the harder case, and the import joins it later at low cost.
− While the parse runs, other requests of the same process are slower (the parse holds the interpreter's global
  lock). K-10a bounds it; it does not remove it.
− The in-process rate limit counts per process; with several API instances (M7) the limit must also be enforced at
  the proxy (as for login, `core/ratelimit.py`).
− Retention (K-10b) deletes data the design note said to keep; the stored rows of an applied import are kept.
## Alternatives
- **Move the import to the worker now.** Safest isolation, but needs file storage, a new job type, a processing
  state and polling in the UI, for a trusted-role, bounded-cost input. Rejected for now; revisit when the M6
  worker exists (decision 3).
- **Keep as is, no extra controls.** Leaves G1 and G2 open; one stolen admin account could slow every coaching and
  fill the disk. Rejected.
- **Tighten the limits further (fewer rows or MB).** Cuts the worst case but also real syllabus files (20,000 rows
  is generous; a full JEE/NEET syllabus is a few thousand). Not needed once K-10a exists.
