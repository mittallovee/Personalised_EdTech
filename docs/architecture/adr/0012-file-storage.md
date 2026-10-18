# ADR-0012: Storage interface — local disk → S3/GCS
- Status: Proposed · Date: 2026-10-18
## Decision
`core/storage.py` defines `put/get/delete/presign` with opaque keys `org/{org_id}/{kind}/{uuid}`. Local implementation writes to a Docker volume; cloud implementation uses S3 or GCS. Clients never see storage paths; downloads go through authorized API endpoints or short-lived signed URLs. Files are immutable once written; checksums (SHA-256) stored in DB.
## Consequences
+ Same code locally and in cloud. − Signed-URL behaviour differs per backend (covered by adapter tests).
