# ADR-0024: Untrusted documents are parsed only in a sandboxed worker
- Status: Accepted (owner approved the M6 design note, 28 Nov 2026) · Date: 2026-11-28 · Refines ADR-0007, ADR-0018

## Context
M6 lets members upload PDFs, Word files and photographs. ADR-0018 kept the small syllabus spreadsheet inside the API
request and said untrusted documents would go to a worker; K-17 asked for that worker and a threat model
([threat-model-uploads.md](../threat-model-uploads.md)). PDF, image and Office parsers have a long history of memory and
parsing bugs, and one API process serves every coaching.

## Decision
- Documents are opened **only** by the **sandboxed worker** (`python -m qbank.ingest_worker`). The API process stores the
  bytes and queues a job; it never parses. The code that opens documents lives in `qbank.modules.ingestion.render`, and an
  import-linter contract fails the build if anything but the sandbox worker imports it.
- The worker runs as its own compose service: **no route out** (its only network is an internal one that holds the
  database), a read-only filesystem with a small scratch folder, all Linux capabilities dropped, no new privileges, capped
  memory (1 GB), processor (1) and processes (128). A unit test reads `compose.yaml` and fails if any of this is loosened.
- It uses its **own database role**, `qbank_ingest`: not a member of `qbank_app`, able to run the job functions and to touch
  only the upload tables of the job's own coaching, protected by the same row-level security. It cannot read questions,
  users, AI keys or any other table; a test lists every table and checks each is closed to it.
- Jobs are claimed by type (`jobs_claim_for`): the sandbox takes only `ingest.render`; the normal worker never does.
- Word files are read directly as XML parts (option A of the design note); no office suite is run. A converter such as
  LibreOffice would be a separate decision with its own threat review.

## Consequences
+ A parser bug is contained to a worker with no network and almost no database rights.
+ The rule is checked on every change (import contract, compose test, role test), not remembered.
− A third database role and a third container to run and monitor.
− The sandbox shares the storage volume with the API (it must read originals and write page pictures); a compromised
  sandbox could read other coachings' files on that volume. Narrowed in the cloud by per-job signed access (M7); recorded as
  a residual risk in the threat model.
− Parsing speed is bounded by the caps; large files take longer.

## Alternatives
Parse in the API process with limits (as ADR-0018 does for a 5 MB spreadsheet): rejected, a document parser is a much bigger
target. Run parsers in a per-file throw-away container: stronger, but needs a container runtime the cloud choice (M7) has not
made yet; the design keeps the interface so it can be adopted later.
