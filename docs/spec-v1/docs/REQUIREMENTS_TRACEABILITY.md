# Requirements Traceability

Consolidated 18 October 2026. Requirement IDs R-01–R-39 retained. Confirmed policy is elaborated in domain specifications; observable checks below remain **planned**, with technical defaults labeled in P-01–P-35. No application tests have run.

| ID | Requirement | Observable criterion | Decisions | Release | Planned scenarios |
| --- | --- | --- | --- | --- | --- |
| R-01 | Tenant isolation and initial rollout | One coaching initially; two-tenant read/write/worker/storage/graph/copy denial checks, with explicit full platform authority. | D-01/D-02 | 1 | AT-01–04, AT-36–40 |
| R-02 | Identity, onboarding and permissions | Verified Google/password/OTP linkage, one-coaching faculty, concurrent sessions, no device-manager UI; correct Owner/admin/faculty/platform authority and revocation. | D-02/D-03 | 1 | AT-13, AT-24, AT-34–40 |
| R-03 | Coaching owns content | Faculty/admin removal preserves content, creator attribution, versions and usage history. | D-19 | 1 | AT-13, AT-34 |
| R-04 | Bulk source upload | PDF/DOC/DOCX/images, mixed submissions, per-file limits/signature validation and partial errors. | D-10 | 1 | AT-05, AT-07 |
| R-05 | Private original lifecycle | Faculty view; admin storage/delete; retain until deletion; preserve questions/required assets and honest unavailable status. | D-19 | 1 | AT-22 |
| R-06 | Nonblocking durable ingestion | Further uploads/navigation while jobs persist; accurate stage/unit/per-file progress. | D-12 | 1 | AT-08, AT-27 |
| R-07 | Recoverable idempotent jobs | Retry/cancel/races preserve partial drafts, human work and stable identities; same key/different payload conflicts. | D-12 | 1 | AT-06, AT-08, AT-27 |
| R-08 | Text, scan and handwriting | Preserve source anchors, equations, figures and question/solution associations; uncertain recognition flagged. | D-11 | 1 | AT-07, AT-43 |
| R-09 | Legacy/modern Word | DOC/DOCX with original and conversion/assets/provenance retained, no macro execution. | D-10/D-11 | 1 | AT-05, AT-07 |
| R-10 | Structured segmentation and file pairing | AI identifies paper/key/solution associations, faculty corrects; unmatched/conflicting evidence remains visible. | D-07/D-10 | 1 | AT-07–09 |
| R-11 | Manual/import convergence | Same type-aware validation and downstream QC; no invented source anchors for manual input. | D-07 | 1 | AT-09, AT-12 |
| R-12 | Staging before publication | Incomplete candidates saveable; extraction/AI success cannot imply human QC/publication. | D-05 | 1 | AT-08–09, AT-13 |
| R-13 | Master/code/version and passage identities | Eight-character global code distinct from UUID/version; passage children separately coded with pinned context. | D-06/D-08 | 1 | AT-10–12 |
| R-14 | Secure global codes | Cryptographic generation/global uniqueness/collision retry; proposed case/alphabet/non-reuse tested when implemented. | D-06 | 1 | AT-10 |
| R-15 | Stable published history | Old revisions/assets/passage/labels persist; correction same code/new version; current workflow evidence bound to revision. | D-08 | 1 | AT-04, AT-11–13 |
| R-16 | Nine formats and rich equations | Exact option/numeric/matching rules; no separate numerical-unit field; visual/LaTeX/MathML and flagged precision. | D-07 | 1 | AT-12, AT-29 |
| R-17 | AI taxonomy and knowledge graph | Singular chapter/topic, primary/multiple secondary concepts, required difficulty/Bloom/PYQ metadata; provisional immediate concepts/same-subject cross-class prerequisites; admin review, faculty graph, seven-language catalogue. | D-09/D-11 | 1 | AT-12–13, AT-21, AT-23, AT-32–33, AT-48 |
| R-18 | Question relationships | Variants/translations distinct new codes and exact source-version links; independent updates. | D-14/D-15 | 1 | AT-10–11, AT-15 |
| R-19 | Independent formal actions and optional solution | QC/approve/publish separately granted, shared queue, authorized self actions, return/correct/resubmit; no solution requirement. | D-03/D-05 | 1 | AT-13 |
| R-20 | Safe audit/provenance | Current metadata in normal UI; internal actor/revision/action/AI evidence retained without secrets. | D-20 | 1 | AT-14, AT-19, AT-23, AT-31 |
| R-21 | Provider choice and on-demand AI tools | Google/Anthropic/OpenAI/OpenRouter plus extension; coaching keys/enabled models/visible fallback; variants count/type/difficulty/mixed/instructions preserving primary concept; diagrams/solve/check; one-question opt-in correction. | D-13 | 1 | AT-14, AT-26, AT-30–31 |
| R-22 | Direct validated AI metadata | Fill editable values without per-field approval; correctable, provenance-bound, no published silent writes. | D-09/D-13 | 1 | AT-14, AT-21 |
| R-23 | Honest verification | Advisory checks are not human QC or an earned AI-verified badge; evaluated criteria required for such a claim. | D-13 | 1 | AT-14, AT-30 |
| R-24 | Duplicate checking and requested translation | Every new intake checked within coaching; human exact duplicate attaches source/no new code; translation after source QC on request. | D-14/D-15 | 1 | AT-15 |
| R-25 | Bank search/filter/counts | Bounded pages/results and counts share tenant/permission/filter scope. Bank search belongs to release one; test assembly later. | D-16/D-20 | 1 | AT-16, AT-41 |
| R-26 | Tests pin exact versions | Later test preserves selected versions despite corrections. | D-16 | Later | AT-11, AT-17 |
| R-27 | Test/batch duplicate control | Later selection applies reviewed duplicate policy/override with evidence. | D-14/D-16 | Later | AT-17 |
| R-28 | Test history/export | Later history retains criteria and version pins; approved export samples verified. | D-16 | Later | AT-17 |
| R-29 | Student analytics | Later approved access/attempt/event/privacy/retention contract before collection. | D-17 | Later | AT-20 |
| R-30 | Usable faculty UI and branding | Responsive/keyboard/clear errors proposed baseline; platform-only per-coaching name/logo, tenant-safe rendering/common entry. | D-20/D-01 | 1 | AT-18, AT-39–40 |
| R-31 | Observability and safe operations | Correlated API/worker failures/retries, no secrets/foreign data in logs. | D-18 | 1 + production gates | AT-19 |
| R-32 | Migrations/verification | Disposable PostgreSQL migration and actual runtime-role tenant/immutability checks; report evidence only after execution. | D-04/D-18 | 1 | AT-04, AT-19 |
| R-33 | AI/file resource controls | Admin faculty actual/estimated/unknown usage; configured monthly limits 80% warning/100% stop/calendar reset/history, bounded concurrent reservations. | D-10/D-13 | 1 | AT-05, AT-19, AT-25–26 |
| R-34 | Archive, backups and retention | Creator/admin archive/restore preserves codes/history; protected original deletion; backup/restore proposal and later production targets. | D-18/D-19 | 1 + production gates | AT-22, AT-28 |
| R-35 | Lakh-scale bank | Measure bounded search/filter/count/graph/duplicate/jobs with actual workload/environment; few faculty does not imply tiny corpus. | D-18/D-20 | 1 evidence gate | AT-41 |
| R-36 | Reusable extraction patterns | AI learns unknown layouts, versions/reuses compatible rules, detects drift/coverage, recognizes new handwriting and measures savings honestly. | D-21 | 1 | AT-42–43 |
| R-37 | Courses/live/recorded | Later faculty courses and session delivery with access/enrollment/media contracts. | D-22 | Later | AT-44 |
| R-38 | Personalized AI teaching/videos | Later need/current-level-specific teaching and generated concept videos, evaluated learner/educational/cost evidence. | D-22 | Later | AT-45 |
| R-39 | Independent complete coaching copy | Platform-only educational snapshot/patterns/assets/history, independent IDs/new codes, published status retained, no sync/users/keys/grants/spend replay. | D-23 | 1 | AT-46–47 |

Bank search/filter/counts (R-25) is release one; test assembly/version pins/batch rules/exports (R-26–R-28) are later. Historical interview drafts incorrectly grouped bank search with the later test builder; this consolidation corrects that categorization without adding a feature.

Source samples, exact model availability and numerical performance/savings targets remain evidence gates. The current interview is closed. [PRD](PRD.md), [decision register](PRODUCT_DECISION_REGISTER.md), [acceptance plan](ACCEPTANCE_TEST_PLAN.md), [readiness](DOCUMENTATION_READINESS.md).
