# Test Builder and Future Analytics

## Test-authoring specification questions

Test creation and test-paper exports are explicitly deferred until after the first question-bank release. The design below is later scope; scoring, sections, batch, selection and export choices do not block the first database/question-bank milestone.

### Proposed reproducibility contract

- Every saved item references an exact question version and has a defined item position/section.
- A test version preserves question/version selection and selection criteria. Whether drafts can change in place versus full revision storage is open.
- Historical rendering preserves content, options, answer/solution access policy, language, assets and relevant metadata. Current master/taxonomy changes must not silently alter history.
- Eligibility uses the selected organization's publication/approval policy; search counts cannot reveal inaccessible candidates.
- Duplicate/near-duplicate enforcement uses the reviewed canonical/variant rules, defined scope and override authority. Similarity scores alone are not final duplicate decisions.
- Export must render the pinned content and apply an explicit answer-key/solution inclusion policy. Export formats and acceptance examples remain open.

### Later student discovery

Attempt lifecycle must define started, resumed, submitted, timed-out and invalidated behavior, server/client time semantics, answer autosave/idempotency, and authorized test access. These are future design topics, not a first-prototype commitment. Privacy, consent where applicable, event semantics, retention and access must be reviewed before collecting student events.

Do not infer learning gains from raw response-time or wrong-option metrics. Recommendation quality needs educational evaluation and explainable links to evidence. No student analytics tables or event collector are specified as ready to build.

## Test builder requirements
- Filter questions by subject, chapter, topic, concepts, difficulty, question type, exam/year, language, source, video solution availability, and status as permissions allow.
- Show counts for the current filter and selected criteria.
- Assemble tests from specific immutable question versions.
- Prevent duplicate/near-duplicate questions in the same test or configured batch.
- Preserve test version/history and a snapshot of selection criteria.
- Enforce that only eligible approved/published questions can be selected according to policy.

## Future student app
- Secure test access and submission.
- Attempt state, timing, and answer capture.
- Preserve question-version references used during attempt.
- Analytics for time per question, accuracy, wrong options, concept-level performance, and recurring misconceptions.
- Personalized recommendations should be explainable, privacy-aware, and validated for educational usefulness.

## Data design caution
Do not build analytics tables before defining event semantics, retention, and consent/privacy requirements. Keep raw events and derived aggregates distinguishable.

## Video solution link only — confirmed

User-confirmed: video solutions use a stored external video link; video-file upload/hosting is not required for the first release. Video solution metadata remains optional under the handover. Validate safe URL structure and preserve the link in version-scoped metadata; do not fabricate a video URL or claim external content is hosted/archived by this platform. Existing edit permissions and published-version rules apply to link changes. Link/player UI details remain design work; no streaming service or provider has been selected.

## Later learning beyond tests — confirmed expansion

The future student platform includes faculty courses/live classes/recorded sessions and AI teaching/concept videos personalized to needs/current level. Link learner evidence to concepts/prerequisites; distinguish class, question difficulty and mastery. Enrollment/media/event, AI trigger/review and educational evaluation contracts remain later work. The first-release external question-video link remains unchanged. See [future learning](FUTURE_LEARNING_AND_AI_TEACHING.md).
