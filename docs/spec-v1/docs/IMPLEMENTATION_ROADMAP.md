# Implementation Roadmap

Consolidated 18 October 2026. Requirements interview is closed; documentation package is ready for review. **Application implementation has not started.** Internal build slices are not permission to drop any release-one feature.

## Current review deliverable

Review master context, PRD, decisions, permissions, all type examples, lifecycle, architecture/schema/API and technical defaults. Engineering recommendations are labeled P-01–P-35. Source samples and production hosting/budget remain deferred. No more routine feature questions are required.

## Proposed build sequence after document review

| Slice | Concrete scope | Exit evidence |
| --- | --- | --- |
| 1 — Local foundation | Verified local runtime; API/web shell, PostgreSQL, migrations, tenant context and minimal master/version/revision records | Local startup/restart, disposable migration, tenant denial, stable code and immutable published snapshot checks |
| 2 — Identity/admin | Verified alternative login methods/linkage, sessions, coaching/first Owner, faculty/admin grants, ownership transfer, platform branding/full access | Role/owner/race/revocation checks and real auth integration evidence |
| 3 — Manual bank/QC | All answer formats, rich equation editor, save/revision/QC/approve/publish, search/filter, archive/restore, graph catalogue foundations | Schema/render fixtures, concurrency, required-field and permission checks |
| 4 — Sources/background intake | Bulk documents/images, private originals/assets, jobs/cancel/retry/checkpoints, paper/key/solution associations | Per-file errors, safe restart, partial drafts, source/asset preservation |
| 5 — Extraction/patterns | Text/OCR/handwriting paths, AI layout discovery, validated pattern reuse/drift/fallback and duplicate staging | Representative sample quality/coverage evidence; honest cost/time comparisons |
| 6 — AI/graph/admin | Four provider adapters, enabled models/coaching keys, direct tagging/provisional graph, on-demand tools, budgets/reports/app alerts | Verified capability catalogue, billing/reservation/fallback, revision-safe AI and taxonomy tests |
| 7 — Independent seeding | Platform copy manifests, mapped educational dataset/patterns/assets/history, preserved publication | Two-coaching copy/retry/non-sync/secret exclusion and dependency integrity evidence |
| 8 — Release-one integration | Complete agreed question-bank workflows on local PC | All applicable acceptance scenarios, sample limitations, documented observed capacity and unresolved defects |

AI adapter/budget foundations may be developed before extraction where dependencies require them. This table is delivery organization, not a rigid prohibition on overlapping module design.

## First executable slice for review

Proposed first result: a local web/API health path and PostgreSQL migration containing organizations, minimally trusted synthetic test identities, question master/version/revision and audit; default-deny tenant transaction context and protected immutable snapshots.

A synthetic identity harness is only for isolated foundation fixtures. It is not complete authentication or permission to expose business APIs publicly. Formal Google/password/OTP setup follows slice 2. No live AI calls, uploaded customer corpus or paid hosting is required for slice 1.

Planned acceptance: two tenant fixtures cannot read/write each other's data; missing context fails closed; code collision retry preserves uniqueness; a saved revision cannot be overwritten; published update rejected/new correction version succeeds; stale revision conflicts; migration and local restart preserve persisted fixtures. Test scripts/results are produced only after implementation authorization and actual execution.

## Later modules

- Test builder/scoring/paper export with pinned question versions.
- Student enrollment/attempts/analytics/mastery/recommendations and privacy requirements.
- Coaching subscription/payment collection.
- Faculty courses/live classes/recorded sessions.
- AI teaching and concept videos personalized to student needs/current level.

Relative order/cost/schedule for these later modules is not committed. They require their own milestone design, not more questions in the current round.

## Definition of done

A slice is done only when its code, migrations, relevant tests and observed results exist, with docs updated to actual behavior. No planned test is counted as passed. Release-one completion needs representative extraction/provider/content evaluation and all relevant authorization/tenant/version/asset/copy controls. Local documentation checks alone do not meet these gates.
