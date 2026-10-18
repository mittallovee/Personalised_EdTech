# Project Master Context

Consolidated: **18 October 2026**. Current requirements interview is complete. Documentation/design review is the current activity; no application code, services, migrations, accounts or provider integrations exist.

## Product and delivery boundary

Build an organization-owned question bank for coaching institutes, initially focused on JEE/NEET and Physics, extensible to other subjects/exams. Start with one coaching and very few faculty, while supporting many isolated coachings and a bank expected to reach lakhs of questions. These are qualitative workload expectations, not verified capacity or numeric guarantees.

The first release includes manual entry, bulk PDF/DOC/DOCX/image ingestion, printed/scanned/handwritten questions and solutions, asynchronous extraction/staging, all nine question formats, correction/QC/approval/publication, search/filter and concept navigation, AI assistance and controlled administrative dataset copying.

Test creation/paper export, student attempts/analytics/recommendations, subscription/payments, courses/live/recorded sessions and personalized AI teaching/concept videos are later phases. Source samples will be supplied later; do not repeatedly request them or block documentation.

## Confirmed platform and access

- One common app entry URL; per-coaching name/logo, edited only by platform admin.
- Platform admin creates coachings and their first Owner and has full supported application access across coachings. Normal validation, organization ownership, immutable published history and audit still apply.
- Coaching Owner appoints/removes other admins and can transfer ownership to another active same-coaching admin; former Owner remains regular admin. Multiple admins are supported. Owner chooses demotion to faculty or app removal when removing an admin.
- All coaching admins invite/create and remove ordinary faculty. No public coaching self-signup. Removal revokes access but preserves coaching-owned content and historical attribution.
- Faculty account belongs to one coaching; no organization switcher. Faculty sees the complete own-coaching bank and available original sources.
- Upload/manual/AI tools are available to all faculty by default. Formal QC, approve, publish and cross-author editing are independent admin-granted permissions. Authorized self-review/approval/publication is allowed. QC uses a shared queue without mandatory assignment.
- Google, email/password and mobile OTP are alternative login methods linkable to the same verified canonical account. Concurrent mobile/laptop sessions are supported. No logged-in-device list or remote per-device logout UI.
- Notifications are **in-app only**. AI taxonomy/concept/prerequisite additions notify all active coaching admins including Owner. No notification-email requirement; existing authentication methods remain.

## Confirmed question behavior

Internal UUID, globally unique permanent eight-character alphanumeric code and version identity are separate. Corrections create versions under the same code; variants/translations are new masters/codes linked to exact source versions. Published content/assets/passage references remain stable. Archive/restore preserves identity/history; admin or original creator may act within the confirmed scope.

All nine formats and numerical/matching constraints are in [the type specification](QUESTION_TYPES_SPECIFICATION.md). A passage child is its own coded question with a concrete answer type and shared context; passage is not a second answer format.

Publication requires valid content/answer, class, subject, exactly one chapter/topic, primary concept, difficulty 1–10, Bloom level and authorized QC/approval/publication. PYQ additionally requires exam/year. Solution, subtopic, video link, PYQ date/shift/paper code are optional. Visual, LaTeX and MathML equation entry are included.

## Confirmed AI, taxonomy and sources

Taxonomy supports class/subject/chapter/topic/subtopic, primary and multiple secondary concepts, and same-subject prerequisite links across classes. AI creates/maintains the catalogue and fills metadata directly. Missing concepts/prerequisites may be added and used immediately as AI-added/admin-review-pending; admin later approves, edits, merges or revokes as applicable. Only admin and the authorized AI workflow create catalogue entities. Faculty can view the concept graph/open linked questions and correct question assignments under edit permissions.

Initial question languages: English, Hindi, Gujarati, Bengali, Marathi, Telugu and Tamil; admin may add languages. Display one at a time; metadata follows question language without mandatory English duplicate. Translation runs on faculty request after source review, uses a new code, and can evolve independently.

Each coaching adds its own Google, Anthropic, OpenAI and OpenRouter credentials; support adding providers later. Coaching admin controls enabled supported models/default; faculty selects compatible enabled models. On failure show a safe error and try a bounded compatible fallback using the same coaching's keys/budget. Admin sees faculty-wise usage/cost, with actual/estimated/unavailable evidence. Monthly faculty budgets warn at 80%, stop new AI at 100%, reset each calendar month and retain history.

On-demand variants may change count/type/difficulty, mix targets, accept extra instructions and preserve primary concept; source review is not required. Diagram generation/editing, missing-answer solving and existing-answer/solution checks are faculty-requested. Corrections are suggested/flagged; one-question explicit opt-in may apply changes, still displaying old/new values/reason and respecting edit/version rules. AI output is not human QC or automatic publication/verification.

Uploads: 50 MB/document and 10 MB/image. Keep originals until admin deletion, with admin storage analytics. Faculty may view available originals. Delete must preserve saved questions and required independent assets.

Jobs run in background while new uploads/other work continue. Faculty cancels own jobs; keep extracted unpublished drafts and any already reviewed/published work. AI links separate papers/keys/solutions; faculty can correct associations.

Unknown document layouts use initial AI discovery/extraction and save reusable versioned patterns. Compatible later files automatically reuse them with coverage/drift checks and fallback; support multiple layouts and handwriting. Patterns do not cache old answers or remove the need to recognize new handwriting. Savings/accuracy remain unverified.

Coaching data/patterns are separate by default. Platform admin may make a complete one-time independent educational-data copy to another coaching, including patterns/assets/provenance. Destination receives new identities/global codes, retains published snapshots as published, and may edit independently; no synchronization. Users, sessions, permissions and provider keys are excluded.

## Architecture and next action

Agreed architecture: modular monolith with durable background workers and tenant-safe API/database/storage. Development runs on **this PC**. Production hosting/budget are deferred.

[Architecture](SYSTEM_ARCHITECTURE.md), [schema](DATABASE_SCHEMA.md), [contracts](API_CONTRACTS_DRAFT.md) and [technical defaults](TECHNICAL_DESIGN_PROPOSALS.md) contain concrete engineering proposals, not new approved product facts. Next step is review of this consolidated package and the [first implementation slice](IMPLEMENTATION_ROADMAP.md). Do not interpret documentation authorization as authorization to begin application implementation.

## Authority and history

Confirmed product policy takes priority over engineering proposals. Current specialized specs and the decision register govern their domains. The interview drafts are preserved in the historical review ZIP; superseded policies there are not active requirements. No application tests, OCR evaluations, provider calls or performance benchmarks have run.
