# Product and Technical Decision Register

Consolidated 18 October 2026. IDs D-01–D-23 are retained. Confirmed policy is distinguished from proposed implementation in [technical defaults](TECHNICAL_DESIGN_PROPOSALS.md).

| ID | Current product decision | Engineering follow-through / milestone |
| --- | --- | --- |
| D-01 | One initial coaching; multi-coaching architecture; shared entry URL and platform-only name/logo editing | Tenant-safe rendering; no separate tenant domains required |
| D-02 | Google/email-password/mobile OTP, verified canonical-account linkage, one-coaching faculty, admin onboarding, concurrent devices; no device-manager UI | Proposed server sessions and identity adapter; real OAuth/OTP provider configuration before activation |
| D-03 | Default faculty view/upload/manual/AI; independent QC/approve/publish/cross-author-edit grants; shared QC queue, authorized self actions | Fixed initial roles plus independent action grants; see permission matrix |
| D-04 | Modular monolith/workers architecture; implementation stack not user-selected | Next.js/FastAPI/PostgreSQL/SQLAlchemy/Alembic/Linux Celery/Redis proposed; pin supported compatible versions during foundation |
| D-05 | Human QC, return/correct/resubmit, optional solution and required publication fields | Concrete revision-bound transition proposal in lifecycle |
| D-06 | Eight alphanumeric characters, globally unique; UUID/master/version distinct | Proposed uppercase A–Z/0–9, secure generation/collision retry and permanent non-reuse |
| D-07 | All nine formats and answer constraints confirmed | Schema/examples define rich blocks, stable option IDs, precise decimal strings and passage context |
| D-08 | Published history immutable; corrections use same code/new version | Proposed append-only draft revisions, ETags, revision-bound QC/approval invalidation |
| D-09 | Detailed AI-managed taxonomy; direct metadata; immediately usable provisional concepts/prerequisites; admin later review; faculty graph view | Stable hierarchy/concept IDs, localized labels, same-subject cross-class prerequisite DAG proposal |
| D-10 | Bulk PDF/DOC/DOCX/images, 50 MB/document and 10 MB/image; source retention | Proposed exact byte/extension limits, isolated legacy conversion, private local asset store |
| D-11 | Initial seven languages/admin extension; printed/scanned/handwritten questions and solutions | Recognition/conversion quality unverified; benchmark representative later samples |
| D-12 | Nonblocking jobs/further uploads; faculty cancels own jobs; retain extracted drafts and published work | Proposed durable checkpoints, bounded retry, cooperative cancellation and idempotent outputs |
| D-13 | Google/Anthropic/OpenAI/OpenRouter and future extension; coaching keys; enabled/default models; visible compatible fallback; confirmed AI tools; monthly budgets 80%/100%/calendar reset | Capability-verified adapters; proposed reservations/accounting/secret lifecycle; no model quality or price claims |
| D-14 | Automatic same-coaching duplicate check; human exact-intake decision attaches source without new code; variants/translations distinct | Proposed normalized evidence + bounded retrieval; existing duplicate masters remain non-destructively linked |
| D-15 | Faculty-requested translation after source review, new master/code, independent updates, one display language | Exact source-version links and own QC; no publication prerequisite on source |
| D-16 | Release one question bank; tests/paper export later | Later scoring/layout/export/version-pin design |
| D-17 | Student product/analytics/recommendations later | Enrollment/privacy/attempt/event/mastery contracts at that milestone |
| D-18 | Development hosted on this PC | Local environment proposed; production hosting/budget/recovery targets deferred |
| D-19 | Retain originals until admin deletion; admin storage analytics; faculty source view; creator/admin archive and restore preserving history | Independent asset ownership, source tombstones, backup/restore proposal |
| D-20 | Normal UI current metadata; internal audit; seven languages; common app behavior | Responsive/accessibility baseline proposed; no forced bilingual question display |
| D-21 | AI learns/reuses multiple layout patterns, supports handwriting, validates drift/coverage; samples later | Versioned configuration, scoped pattern selection, coverage manifest and evaluation plan |
| D-22 | Courses/live/recorded sessions and personalized AI teaching/concept videos later | Separate learner/media/cost/evaluation contracts |
| D-23 | Separate coaching data/patterns; platform-only complete one-time independent copy; published status retained; new codes; no users/keys/sync | Proposed manifest/snapshot/import namespace and resumable dependency mapping |

## Current administrative rules

Platform admin has full supported application authority across coachings. Owner manages other admins and transfers ownership to an active same-coaching admin; previous Owner remains regular admin. Owner chooses admin demotion to faculty versus app removal. All coaching admins may invite/create/remove ordinary faculty. Account removal revokes access and preserves organization-owned work.

Notifications are in-app only to all active same-coaching admins including Owner. Provider keys are coaching-owned. Neither copied provenance nor a matched email grants user membership or permissions.

## Superseded decisions

| Earlier interview statement | Current rule |
| --- | --- |
| Locate an existing codebase before starting | No prior code exists; documentation first |
| AI taxonomy must wait for admin approval | Immediately usable provisional addition; admin later review |
| Multiple-correct requires at least two correct choices | One or more correct choices are valid |
| Platform admin only views/edits a subset | Full supported application access with validations/audit |
| App and email taxonomy notifications; mandatory alert-email contact | App notifications only; notification-only contact rule withdrawn |
| Open test/export scope for first release | Test creation and paper export later |
| Hosting and monthly cloud budget block current review | Local development on this PC; production choices later |

## History and review

Detailed chronological interview drafts are preserved in [the historical archive](../question-platform-review-history-2026-10-18.zip); the original handover remains unchanged. This register supersedes stale open questions in those historical drafts. Technical proposal IDs P-01 onward are not additional confirmed product answers.

No current required user questionnaire remains. Review the concrete document set and proposed first slice; do not reopen settled policy through repeated small feature questions.
