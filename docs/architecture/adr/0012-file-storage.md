# ADR-0012: Storage interface — local disk → S3/GCS
- Status: Accepted (M3 PR 3g-1) · Date: 2026-10-18
## Decision
`core/storage.py` defines `put/get/delete/presign` with opaque keys `org/{org_id}/{kind}/{uuid}`. Local implementation writes to a Docker volume; cloud implementation uses S3 or GCS. Clients never see storage paths; downloads go through authorized API endpoints or short-lived signed URLs. Files are immutable once written; checksums (SHA-256) stored in DB.
## How it was built (M3 PR 3g-1)
- `Storage` has `put`, `get` and `delete`; `presign` is added with the first cloud backend, because the local
  one has nothing to sign and the API serves files itself (`GET /api/v1/assets/{id}/content`, which checks the
  caller's coaching on every request).
- `put` never replaces a file: it writes beside the target and links it into place, so a reader never sees a
  half-written file. Keys are checked (letters, digits, `-`, `_`, `/`; no dots), so a key cannot leave the folder.
- The `assets` row is written once and never changed or deleted by the runtime role; the file is stored first and
  removed again if the row cannot be written. A file with no row (a crash between the two) is harmless and is
  swept by the M7 clean-up job.
- Pictures are sent as the raw request body (like the syllabus import, ADR-0018), not as multipart form data, so
  no multipart parser (and no `python-multipart` dependency) is exposed to uploads.

## Consequences
+ Same code locally and in cloud. − Signed-URL behaviour differs per backend (covered by adapter tests).
