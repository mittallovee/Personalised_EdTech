# Permissions Matrix

Consolidated 18 October 2026. Confirmed access policy. Owner/admin includes normal coaching management authority; fixed-role implementation and own-draft defaults are proposed in P-07/P-08. Platform admin has full supported access across all coachings, with validation/version/audit rules.

| Capability | Faculty | Coaching admin / Owner | Platform admin |
| --- | --- | --- | --- |
| View complete own-coaching bank and available originals | Yes | Yes | Any target coaching |
| View graph and open primary/secondary linked questions | Yes | Yes | Yes |
| Upload/manual entry/AI tools | Default, no per-user enable flags | Yes | Yes |
| Choose enabled compatible AI model | Yes | Yes; configure enabled/default | Yes; protected configuration |
| Edit own unpublished work | Proposed default | Yes | Yes |
| Edit another creator's work | Separate admin grant | Yes | Yes |
| Formal QC/pass/return for correction | Separate QC grant | Yes | Yes |
| Approve | Separate approve grant | Yes | Yes |
| Publish | Separate publish grant + lifecycle checks | Yes + checks | Yes + checks |
| Approve/publish own content | With matching grants | Yes + checks | Yes + checks |
| Archive/restore | Original creator for own question | Any own-coaching question | Any target coaching |
| Cancel processing | Own job | Own-coaching administration | Any target coaching |
| Storage analytics/delete original files | No | Yes | Yes |
| Faculty-wise usage/cost/budget dashboard | No admin view implied | Yes | Yes |
| Provider key administration | No secret access through tools | Yes, protected/masked | Yes, protected/masked |
| Invite/create/remove ordinary faculty | No | Any admin | Yes |
| Set ordinary faculty action grants | No | Proposed Owner/admin management | Yes |
| Appoint/remove/demote other admins | No | Owner only; choose faculty/app removal | Yes |
| Transfer ownership | No | Current Owner to same-coaching admin | Yes |
| Create coaching/first Owner | No | No | Yes |
| Change coaching name/logo | No | No, including Owner | Yes only |
| Create taxonomy hierarchy/concept identities | No | Yes; also authorized AI | Yes |
| Approve/edit/merge/revoke provisional concepts | No | Yes | Yes |
| Correct/revoke prerequisite edges | No | Yes; authorized AI may add | Yes |
| Change question taxonomy assignments | With question-edit authority, choose existing nodes | Yes | Yes |
| Add language catalogue entry | No | Yes | Yes |
| Receive taxonomy review app notifications | No admin entitlement implied | All active admins including Owner | Explicit target administration; no blanket broadcast inferred |
| Initiate complete cross-coaching educational copy | No | No, including Owner | Yes only |
| Hard-delete protected question history | No | No through archival workflow | No extra hard-delete feature introduced |
| Student/test/course/live/video modules | Later | Later | Full authority applies when supported later |

## Rules applying to every action

- Faculty is single-coaching; membership/role/grants must be current.
- Viewing or AI access grants no cross-author write, formal QC, approve or publish right.
- Any QC-authorized faculty may use the shared review queue; no assignment required.
- Creator can self-QC/approve/publish only if granted the separate actions; a different person is not mandatory.
- Default AI access remains constrained by compatible supported models, coaching keys, budget and input/revision eligibility.
- Per-question direct-correction consent does not override edit rights. Published corrections create a new working version.
- Removal revokes access, not ownership/history. Only Owner manages peer admins within coaching roles.
- Original deletion preserves saved questions/needed assets. Archive/restore preserves codes/history.
- Platform full access does not bypass content validation, immutable snapshots or source/destination ownership.
- No per-user upload/manual/AI-enable flags, device-manager UI or notification emails.

[Workflow](USER_WORKFLOWS_AND_PERMISSIONS.md), [identity](IDENTITY_AND_ACCESS.md), [lifecycle](QUESTION_LIFECYCLE_AND_QC.md).
