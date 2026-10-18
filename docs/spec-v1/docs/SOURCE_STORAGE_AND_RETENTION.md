# Original Sources — Storage, Access and Retention

Consolidation note (18 October 2026): confirmed policy is retained below; concrete engineering defaults are in [technical proposals](TECHNICAL_DESIGN_PROPOSALS.md). Any remaining engine/library/quality choices are implementation evidence work, not additional required user questions.

Status: product policy confirmed on 17 October 2026; implementation details remain open. No files have been uploaded to an application or deleted by this documentation work.

## Confirmed policy

- Keep original PDF, Word and image files supplied for question ingestion.
- No fixed automatic expiry has been selected. Originals remain until admin chooses to delete them.
- Show storage usage analytics to admin so they can decide when cleanup is needed.
- Only admin may access the storage usage dashboard or delete originals.
- Faculty may view original sources belonging to their organization for review/reference; source viewing does not grant storage-dashboard or deletion access.
- Deleting an original must preserve saved questions and their necessary diagrams/assets, including content needed to render published versions.

"Immutable original" means its stored bytes are not silently replaced. It does not mean admin can never delete the original under this retention policy.

## Proposed dashboard detail

Organization-scoped total bytes/file count, usage by file type, individual file sizes/upload dates and related ingestion status would let admin identify large or old originals. These detailed dimensions and any quotas/alerts are design suggestions, not approved numerical targets. Coaching roles see only their organization's storage; the now-confirmed full platform admin may inspect/manage originals and storage across coachings with explicit context/audit.

## Independent lifecycle of content

| Resource | Meaning | Effect of original deletion |
| --- | --- | --- |
| Original bytes | Uploaded document/image | Removed through authorized deletion workflow |
| Source metadata/reference | Identity, origin, checksum, attribution and location references | Retain the traceability permitted by policy; mark original unavailable |
| Parsed question/version | Saved structured question content | Remains available; published content stays immutable |
| Required question asset | Diagram/image/table needed for saved rendering | Retain independently of original, with version-safe bytes/references |
| Raw intermediate output | OCR/extraction/parser diagnostics | Retention and cleanup policy remains open; do not treat it as an unreviewed duplicate of the entire original forever |
| Backup copy | Recovery media | Separate purge/restore policy still needs definition; do not claim immediate removal from every backup |

Image inputs may also become figure assets. Ownership/reference tracking must distinguish deleting an ingestion original from destroying an asset required by a question. If the same stored object is shared, the implementation needs a safe retention/copy/reference strategy before permitting source deletion.

## Deletion behavior to design

Authorize admin and tenant scope, assess active processing and required references, retain necessary independent assets, record the actor/time/source action and remove original access. Show deletion state honestly: a metadata row or old source link must not pretend bytes remain downloadable. Questions must not disappear through a cascading foreign-key deletion.

Proposed deletion contract: a source pinned by active ingestion/copy returns SOURCE_IN_USE (409) with authorized job references. Admin may cancel that work, await acknowledged completion/cancellation and retry deletion; do not silently cancel it or destroy an in-flight input. Required independent assets are checked before unlinking original ownership. Original re-download/reprocessing is unavailable after deletion unless another authorized retained copy exists. Physical deletion scheduling, failure recovery, audit retention and backups require detailed contracts.

Admin may delete an original without deleting the question. Question archive/restore is resolved in QUESTION_ARCHIVAL.md; no hard-delete feature is implied. Student/privacy lifecycle remains a later milestone.

## Acceptance evidence required

Prove faculty can view permitted sources and cannot view another tenant's source. Prove non-admin cannot query the storage dashboard or delete through API/object paths. After authorized original deletion, saved questions and required assets still render, source availability is accurate, audit evidence exists and future retries report unavailable input clearly.

See R-05/R-20/R-34 and AT-22. These are planned checks, not executed application tests.

## Full platform source/storage authority — confirmed

Platform admin can view all coaching original sources and storage analytics and perform supported original-file deletion/cleanup. The content-preservation, source-unavailable status, required-asset retention and audit rules apply equally. Ordinary coaching faculty cannot delete originals, and coaching admins cannot manage another coaching's storage. See [platform access](PLATFORM_ADMIN_ACCESS.md).
