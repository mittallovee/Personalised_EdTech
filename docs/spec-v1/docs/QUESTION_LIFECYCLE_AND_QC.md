# Question Lifecycle and QC

Consolidated 18 October 2026. Human QC, independent admin-granted QC/approve/publish, correction-return, authorized self actions and published immutability are confirmed. The following exact states and revision mechanics are **proposed** under P-05–P-08.

## Identities and revisions

A candidate is staged manual/imported/generated work, saveable while incomplete. A master is a bank question with internal UUID and permanent global eight-character code. A version is a proposed correction/publication unit under a master. A revision is an immutable saved snapshot within a working version.

Duplicate checks run before materializing new intake: human-confirmed exact duplicates attach source evidence to the existing master and do not allocate another code. Intentional variants/translations materialize separately. Candidate-to-master mapping is idempotent.

One active working version per master is proposed. Saving appends a revision and updates the version's current revision under a compare-and-swap guard. Published versions/old revisions never mutate.

## Proposed transition table

All actions require active tenant membership or full platform authority, matching current revision/ETag, valid references and audit. Admin/Owner/platform have management authority; faculty formal actions need the individual corresponding grant.

| From | Action | To | Actor/check |
| --- | --- | --- | --- |
| DRAFT | Save changes | DRAFT | Creator/admin/cross-author editor; incomplete values allowed, structural safety enforced |
| DRAFT or CHANGES_REQUESTED | Submit | IN_REVIEW | Content editor; required reviewable type content/answer, metadata validation report |
| IN_REVIEW | Return with findings | CHANGES_REQUESTED | QC-authorized actor; reason/findings required |
| IN_REVIEW | Pass QC | QC_PASSED | QC-authorized actor; exact revision and content/publication-check evidence |
| QC_PASSED | Approve | APPROVED | Independently approve-authorized actor; no unacknowledged blocking finding |
| APPROVED | Publish | PUBLISHED | Independently publish-authorized actor; recheck publication validators atomically |
| Any unpublished state | Edit content/metadata/dependencies | DRAFT | Authorized editor; append revision, invalidate current review/approval eligibility |
| PUBLISHED | Start correction | New version DRAFT | Authorized editor; copy snapshot as starting point, retain predecessor/published pointer |
| Any master availability | Archive/restore | Availability flag only | Admin or original creator; does not change version's workflow state |

A single person may perform multiple transitions if holding the corresponding grants. Approval permission is not QC or publication permission. The publish endpoint cannot synthesize missing QC/approval evidence.

Proposed submit validation permits missing publication metadata as visible findings, while QC pass/approval/publication requires the complete publication checklist. Solution remains optional. Do not round an invalid answer merely to pass a state transition.

## Review, concurrency and corrections

Shared pending queue is accessible to any QC-authorized faculty of the coaching; no assignment lock is required. Concurrent reviews/edits use revision/hash and transactional state checks. A stale request returns a conflict with refresh guidance, not last-writer-wins.

QC/approval history is append-only. After an edit, old decisions remain evidence for the old revision but cannot authorize the current revision. Source re-pairing or applied AI corrections affecting content follow the same invalidation rule.

AI metadata is directly populated before review, without per-field acceptance. AI check findings are advisory and revision-bound. Per-question direct-correction opt-in requires current edit authority at application time and displays previous/new values/reason. It never grants formal QC or auto-publication.

Translation requires a source revision with completed QC: QC_PASSED, APPROVED or PUBLISHED under this proposal. A subsequently changed DRAFT revision cannot reuse an old QC pass. Translation output has its own master/code and normal lifecycle. Variant source need not have completed QC.

## Publication and historical rendering

Publication atomically records exact revision, publisher/time, approval/QC references, immutable metadata/label and passage/asset snapshots, then updates the current published pointer. Later versions may supersede the pointer; old published snapshots remain addressable.

Published content copied by platform admin to another coaching retains published state with imported QC/publication evidence and the platform copy action, not fictitious destination reviewers. This is the confirmed copy exception, not a general publish shortcut. Validate complete dependency integrity before activation.

[Publication checklist](PUBLICATION_REQUIREMENTS.md), [permissions](PERMISSIONS_MATRIX.md), [schema](DATABASE_SCHEMA.md), [copy](CROSS_COACHING_DATA_SHARING.md).
