# Platform Admin — Full Application Access

Consolidation note (18 October 2026): current policy is retained below. [Technical proposals](TECHNICAL_DESIGN_PROPOSALS.md), [schema](DATABASE_SCHEMA.md) and [API](API_CONTRACTS_DRAFT.md) now provide concrete implementation recommendations; remaining empirical/engine choices are milestone work, not further required interview questions.


Status: user explicitly confirmed “full access of everything” on 17 October 2026. This supersedes earlier limited platform read/edit scope and the open questions about platform approval/publication, originals, credentials and other application management. No application, accounts or platform administration have been implemented.

## Confirmed authority

Platform admin has full application access across every coaching. No separate permission confirmation or coaching membership grant is needed for each supported capability. Tenant Owner/admin/faculty roles do not inherit platform authority.

| Area | Platform-admin scope |
| --- | --- |
| Coaching and people | Create/manage coaching organizations and first Owners; manage Owners, admins, faculty, memberships and permission configuration across coachings |
| Questions and QC | View, create, edit, formally review/return for correction, approve and publish questions; archive/restore and perform supported content-management actions in any coaching |
| Source/storage | View original ingestion files and retained assets; inspect storage analytics and perform supported original-file deletion/cleanup |
| Catalogue/graph/languages | Manage class/subject/chapter/topic/subtopic/concepts, prerequisite links and supported-language catalogue |
| AI and operations | Manage each coaching's provider configuration/credentials, enabled/default models, budgets, usage/cost analytics and supported background-job controls; use supported AI operations in the selected coaching context |
| Other application features | Full authority over other supported app features, including copy/export/test/student administration when those features reach their approved delivery phase |

This is application-wide authority, not a new requirement to implement every later feature in release one. Test creation/export, student delivery and personalized student recommendations remain in their previously agreed later phases. A role can use supported actions; it does not invent unsupported hard-delete or impersonation workflows. Complete coaching dataset sharing is now explicitly required; sharing is a one-time independent initial copy; detailed mapping/import-state/conflict contracts remain.

## Workflow and integrity remain

Platform admin may carry out review, approval and publication without a coaching-admin permission grant and may act on their own edits under the existing no-mandatory-second-person policy. Required content/type/metadata checks, revision-bound human QC evidence and valid lifecycle transitions still apply. AI output alone is not verification. Editing a published question creates an editable new version under the same master/code; previous published snapshots and history remain intact.

Administrative access does not silently transfer coaching ownership of questions, change original creator attribution, erase audit/usage history or delete assets needed by saved versions. Source deletion follows the agreed retention/content-preservation workflow. Owner changes retain a consistent principal-owner assignment and explicit role-change history; ordinary coaching users still follow the previously agreed Owner/admin rules.

Cross-coaching access belongs to the platform role, not ordinary tenant roles. A write targets an explicit coaching and valid same-coaching concept/asset/source relationships. Any supported transfer/copy workflow must define its own identities/provenance rather than silently link private objects across organizations.

## Proposed enforcement and evidence

Use a trusted current platform-admin identity and explicit operation/target-coaching context at API, service, worker, database/RLS and private-object boundaries. Platform authority must not come from a submitted role label, guessed code or forged tenant header. Revoked authority fails closed; stale content/role changes are handled as conflicts. Broad application rights do not require database owner/migration credentials or disabling tenant isolation for other callers.

Record platform actor, target coaching/resource, operation, before/after change evidence and outcome. Keep the platform actor visible instead of attributing their changes to a faculty member. Partition cached views/context by authority and coaching. Exact routes, authentication provider, initial platform-admin provisioning and session/recovery mechanics remain implementation design.

Provider-credential administration and use are included in full access. Apply the ordinary protected-secret design: no plaintext keys in logs, audit diffs, question content, client bundles or ordinary faculty responses; display/reveal and secret lifecycle mechanics remain security implementation design. AI operations use the selected coaching's keys and recorded budgets; no cross-coaching credential fallback is introduced. Platform admin may explicitly change a budget/model configuration with audit, while dispatch follows the effective saved configuration and 80% warning/100% stop policy.

## Planned acceptance

Exercise full platform administration against at least two coaching fixtures, including QC/approve/publish, original-source access/deletion, storage/usage analytics, roles/owner management, taxonomy and AI configuration/jobs. Confirm tenant users cannot self-promote or invoke platform actions; revoked platform credentials fail; published history, validation, role consistency, required assets, coaching credential attribution and secret-safe audit remain. Existing read/edit tests cover parts of this role, not a product restriction to those actions. No application or provider tests have run.

## Complete dataset sharing - confirmed capability

Platform admin may share a coaching's complete dataset, including its otherwise separate extraction patterns and associated data, with another coaching. This is explicit administration, not automatic global visibility. Use the confirmed independent initial-copy mode without synchronization; finalize mappings, identity/configuration categories and destination conflicts before implementation. See [dataset sharing](CROSS_COACHING_DATA_SHARING.md).
