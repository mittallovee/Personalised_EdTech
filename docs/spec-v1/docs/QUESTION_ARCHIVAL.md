# Question Archival and Historical Preservation

Consolidation note (18 October 2026): current policy is retained below. [Technical proposals](TECHNICAL_DESIGN_PROPOSALS.md), [schema](DATABASE_SCHEMA.md) and [API](API_CONTRACTS_DRAFT.md) now provide concrete implementation recommendations; remaining empirical/engine choices are milestone work, not further required interview questions.


Status: archive action and authority confirmed on 17 October 2026. Admin/creator restore authority is confirmed; detailed UI/state handling and broader deletion/retention policies remain under review. No archival implementation exists.

## Confirmed policy

- Archive removes a question from the active question-bank list while preserving its content and history.
- Organization admin may archive questions within their coaching.
- The creator faculty member may archive their own question.
- Viewing the complete bank or having cross-author edit permission does not itself grant authority to archive another creator's question.
- Preserve permanent code, versions, provenance, audit and required assets. Published versions are not rewritten or deleted.

## Relationship to other operations

Archive is not hard deletion, cancellation of an ingestion job or deletion of an original source file. Original deletion remains admin-only under its separate storage policy. An archived question still has its organization ownership and historical identity; a code must not be regenerated merely because the question leaves the active list.

Query active versus archived availability explicitly rather than deleting rows or silently corrupting search counts. Existing historical references must continue resolving to preserved content. The future test builder must use reviewed eligibility rules while preserving any already pinned versions.

## Design details still open

- Restore preserves the question's code/content/history; admin may restore within their coaching and creator may restore own questions. Exact prior-state/eligibility handling needs design, without silently publishing a draft.
- Archive reason/confirmation, concurrent editing/review behavior and archived-list UI.
- Account deactivation/creator reassignment and wider retention/deletion policy.

Do not infer physical deletion authority or erase protected versions based on this archive decision.

## Acceptance direction

Admin can archive within their coaching; creator can archive own questions; unrelated faculty cannot archive another creator's question by view/edit rights alone. Active-list behavior changes while codes/content/version history/assets remain available under authorization. Cross-tenant and stale-state actions fail. No application tests have been executed.

## Restore authority — confirmed

User selected both: organization admin may restore archived questions in their coaching, and creator faculty may restore their own archived question. Restore changes active availability without creating a duplicate master/code or deleting archival/audit history. It is not a grant to publish newly edited or unreviewed draft content; apply the appropriate existing lifecycle state and preserve published snapshots. Other faculty cannot restore another creator's question through view/edit rights alone.

## Platform role update

Full platform admin may archive/restore questions across coachings through the supported workflow. Coaching Owner/admin/creator restrictions continue for tenant roles. Preserve identity/version/source/asset/audit history; full access does not introduce physical question deletion contrary to the agreed archival workflow. See [platform access](PLATFORM_ADMIN_ACCESS.md).
