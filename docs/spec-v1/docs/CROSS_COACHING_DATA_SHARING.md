# Platform-Managed Complete Coaching Dataset Sharing

Consolidation note (18 October 2026): confirmed policy is retained below; concrete engineering defaults are in [technical proposals](TECHNICAL_DESIGN_PROPOSALS.md). Any remaining engine/library/quality choices are implementation evidence work, not additional required user questions.

Status: capability confirmed on 18 October 2026. Coaching data and extraction-pattern libraries are separate by default. Platform admin may explicitly share a coaching's complete dataset, including patterns and associated material, with another coaching. The confirmed mode is a one-time independent initial copy; destination may use/change it under its own permissions, with no ongoing synchronization. No data has been copied, shared or exported.

## Confirmed policy

- Each coaching has its own question bank, taxonomy/content context and extraction patterns. A pattern match in another coaching does not automatically make its rules or example files available.
- Platform admin can explicitly share the complete coaching dataset with a selected other coaching, including saved patterns and associated data, rather than being limited to individual questions or templates.
- Ordinary coaching Owner/admin/faculty cannot initiate cross-coaching sharing through their tenant privileges.
- Existing platform full access remains; source samples are still deferred and requirements work continues.

The current question-bank/ingestion design must accommodate this administrative capability. Future courses/classes/media extend the dataset only when those modules exist; their delivery phases are unchanged.

## Dataset completeness and manifest — design direction

Represent the operation as a logical organization-scoped dataset transfer/share, not an unrestricted restore of the entire multi-tenant physical database. Build an explicit source-coaching/target-coaching manifest with a consistent source revision/snapshot and included dependencies.

The educational dataset includes question masters/versions/answers/solutions, available originals and source references, diagrams/equations/required assets, passages and relationships, hierarchy/concepts/prerequisites/localized labels, extraction patterns and their versions/configuration/example references, and relevant provenance/history. Future educational modules need equivalent dependency mapping when introduced.

The confirmed initial copy covers educational content and extraction patterns/dependencies. Destination users and provider API keys are set up independently: do not copy source login accounts, sessions, memberships/privileged roles or provider secrets into the receiving coaching. Historical creator/reviewer/model references stay as attributed provenance, not destination login/membership grants. Destination organization identity, Owner and branding remain its own separately managed configuration. Detailed treatment of operational job/accounting references and future learner records requires the appropriate module contract; those references cannot become destination credentials, billable work or active grants merely because they accompany copied evidence.

Retain source attribution and record the actual platform actor/operation. Missing/deleted originals must be reported as unavailable rather than fabricated; required question assets and pattern evidence need a usable authorized destination reference.

## Confirmed mode: independent initial copy

Platform admin creates a one-time initial snapshot/copy in the receiving coaching. It becomes that coaching's independent dataset for use and modification under its own roles/workflow. There is no continuing live access to the source bank and no automatic synchronization in either direction. Later source edits/deletions, pattern changes or revoked administrative access do not propagate into already completed independent copies; destination edits do not alter the source.

New destination question masters receive separate internal identities and new globally unique eight-character permanent codes. Preserve original master/code/version as provenance, not as a duplicated globally unique destination code. Map question versions, passages, related questions, taxonomy/concepts/prerequisites, patterns and assets consistently into the destination. Existing destination duplicates/conflicts need a reviewed disposition rather than a silent overwrite or another replay-created master.

Copy pattern versions/configuration and intended example dependencies into independent destination-owned records. Destination can use/refine/disable its copies without changing the source library, and vice versa. Existing validators and fresh source recognition still apply; a copied pattern is not a guarantee that every future target layout matches.

Preserve available copied originals/required assets through independent destination resource ownership and access/lifecycle references. Physical byte deduplication is an implementation choice, but source cleanup must not break destination data. Original creator/reviewer/model evidence remains imported provenance; do not invent new human approvals or copy privileged user memberships from that history. Source-published snapshots remain published in the independent copy, without mandatory destination re-review. Record imported publication/QC provenance and the platform copy action rather than inventing local human approvals. Later destination edits use a new editable version and normal local QC/approval/publication.

Use a consistent source cutoff/version manifest so concurrent source changes do not create a mixed snapshot. Background execution and retries reuse operation mappings and never synchronize/reapply over later destination edits. User accounts and API keys are excluded from the copy and configured separately. Source-published content retains publication status. Operational-reference treatment, component failure handling and nonempty-target behavior are now concretely proposed in P-31–P-33 and DATABASE_SCHEMA.md; they remain recommendations for review, not newly confirmed product rules.

## Proposed administrative workflow

1. Current platform admin selects source and destination coachings and the independent initial-copy operation.
2. Resolve a consistent complete manifest, dependencies, source availability, identity mappings, compatible pattern/schema versions and destination conflicts.
3. Show the administrative plan/counts/conflicts. A nonempty destination must not be silently replaced. Destination ownership is independent; nonempty-target conflicts require an explicit contract, while validated source-published content retains published status.
4. Execute as an observable background operation with idempotency, resumable per-stage results and attributable source/target audit. Do not block normal app work while processing a lakh-scale bank.
5. Create validated independent destination data, preserving mapped relationships and history; disclose partial/unresolved outcomes rather than mark an incomplete operation complete.

Validate current platform authority, explicit source/target scope and operation state on every protected stage. Tenant users cannot self-grant sharing by submitting source IDs, pattern IDs or global codes. A revoked platform actor cannot continue unauthorized writes; cancellation/in-flight behavior requires a contract consistent with the existing job model.

## Isolation and configuration boundaries

Separate-by-default data/pattern selection remains the rule. Receiver access is to its independent copied dataset, not the source coaching's unrelated/future records. Later source changes are not synchronized. Use tenant-owned destination mappings and independently retained resource references; do not disable isolation globally or allow arbitrary cross-tenant foreign keys.

Coaching-owned AI credentials and budget attribution remain explicit configuration. Sharing must not accidentally trigger cross-coaching credential fallback, copy privileged memberships or attribute a receiver's new usage to a source faculty identity. Users/authentication and API keys are explicitly excluded; set them up in the destination through its normal onboarding/provider configuration. Missing destination keys must not fall back to the source coaching keys.

## Planned evidence

Test separate pattern matching by default, platform-only complete sharing, dependency coverage, source/target roles and audit, question-code/version integrity, pattern/example usability, retry/cancellation/partial outcomes and destination conflicts at representative scale. Verify a receiving coaching gains only intended shared access/data and no unauthorised role/credential inheritance. Verify independent edits, pattern changes and source deletion cannot propagate/break either coaching; new destination master codes are globally unique and copy retries do not duplicate or overwrite later destination work. Verify source users/sessions/privileged memberships/API keys are absent from the copy, historical attribution does not grant access, destination AI uses only its own configured keys, and missing keys leave AI-dependent work unresolved while copied content remains usable. Verify source-published snapshots remain published without a new local review requirement, nonpublished source content is never upgraded by this rule, and later destination edits do not mutate the copied published version. Review the P-31–P-33 manifest/component/import-namespace proposal before implementation. No sharing implementation or test has run.

## Independent destination account and credential setup - confirmed

The receiver starts with copied questions/answers/solutions, sources/assets, taxonomy/graph and saved extraction patterns. Its users are invited/created separately through the existing platform-Owner/coaching-admin onboarding rules; copying a source actor reference cannot enroll that person into another coaching. Configure the receiving coaching's own API keys separately. Existing model compatibility, usage attribution, monthly budgets and missing/invalid-key behavior still apply. Content browsing/manual work does not require a successful AI provider setup.

Copy source attribution as provenance without copying passwords, OTP state, sessions, membership grants or provider secrets. Preserve new destination Owner/branding configuration. Copying old extraction/AI evidence does not enqueue new paid calls or count past source costs as new destination spending. Exact operational-history representation remains schema design. No users, keys or content have actually been transferred.

## Keep source-published questions published - confirmed

A platform-admin initial copy retains published status for already published source questions/versions. The receiver can use them immediately without a new mandatory local review/approval cycle merely because they were copied. Preserve source publication/QC evidence as imported provenance, and record the actual platform copy/import event with source/destination version mapping; source reviewers do not gain destination accounts or permissions.

Validate snapshot content, required dependencies and destination reference mappings before making the copied published version available. The copy must faithfully reproduce the selected source-published content with destination-owned identities/new global codes. Structural/dependency failures are visible operation conflicts/failures, not permission to silently publish changed/incomplete content or falsely report a completed copy. Draft/unreviewed content is not automatically promoted by this rule.

Copied published versions are immutable. If destination later changes a question, create a new editable version under that destination question's permanent code, retaining the copied published version and normal revision-bound review/approval/publication. Source and destination remain independent. No real publication or copy has occurred.
