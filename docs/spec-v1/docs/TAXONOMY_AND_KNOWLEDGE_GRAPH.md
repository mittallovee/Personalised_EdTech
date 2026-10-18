# Taxonomy and Knowledge Graph

Consolidated 18 October 2026. Stable concept structure supports the first-release bank and later personalized learning; student recommendations are not first-release functionality.

## Confirmed classification

Class → subject → chapter → topic → optional subtopic. A publishable question requires class, subject, exactly one chapter/topic and one primary concept. Multiple secondary concepts are allowed without a limit of two. Difficulty 1–10 and Bloom level are required. Metadata labels follow the question language, without mandatory English duplication.

AI creates/maintains the initial catalogue and primarily tags questions from it. Only admin or authorized AI may create class/subject/chapter/topic/subtopic/concept identities; faculty selects existing assignments within question-edit permissions. Changing assignments is not permission to create taxonomy nodes.

## Immediate provisional workflow

AI matches existing identities/aliases first. If a needed concept is missing, it may add and use it immediately as AI-added/admin-review-pending, then continue tagging. Admin may approve, edit, merge or revoke later. Provisional status alone does not block a valid question's publication.

Record parent/subject/language, definition/aliases, source question/AI evidence, creator type/model and revision. Metadata fills directly without per-field acceptance. Normal question UI shows current values; internal audit/provenance remains.

All active same-coaching admins including Owner receive deduplicated in-app review alerts. **No notification email or notification-only email contact.** App delivery state is separate from shared taxonomy review state. Tagging continues even if UI notification delivery is delayed.

## Prerequisite graph

AI also creates directed prerequisite → dependent links in release one. Links may cross classes within the same subject/coaching, including Class 11 prerequisite to Class 12 concept. Cross-subject links are forbidden. They are immediately usable with pending-admin-review status; admin may approve/correct/revoke.

A prerequisite is not a taxonomy parent or a secondary tag. Proposed graph is a DAG: validate same-subject endpoints, self-links and cycles before activation. A cycle/ambiguous relation remains a visible unresolved proposal rather than silently corrupting the usable graph. Exact educational correctness still requires evaluation.

## Faculty navigation and administration

Faculty views own-coaching graph and opens questions where a concept is primary or secondary. Scope nodes/edges/counts/linked-question pages identically to the bank. No graph-write permission is implied.

Admin edits future catalogue/edge state with history. Concept merge proposes a survivor/alias mapping, future assignment redirection and visible impacted-question review, while preserving original published label/concept snapshots. Revocation stops new automatic selection; existing published snapshots remain resolvable. Incomplete drafts referencing revoked concepts surface correction findings.

## Proposed schema and cross-branch rules

Normalized hierarchy tables and stable concept IDs with localized labels/aliases; question revisions pin classification and label snapshots. Primary question chapter/topic remain singular. Concepts may be associated across chapter/topic branches of the same subject; do not remove secondary concepts just because they are outside the primary topic. A primary concept may be provisional and active.

Cross-class prerequisite allowance must not accidentally turn into cross-subject allowance. Hierarchy consistency and graph consistency are checked separately. Catalogue-language extension requires appropriate label/engine capability handling; it is not proof an OCR/model supports that language.

## Later use and evidence

Later mastery/recommendations/AI teaching reuse stable concepts and reviewed graph history; student level is not merely question difficulty/class/Bloom. Actual mastery signals and recommendation evaluation belong to the later phase.

No taxonomy engine, graph tests, label conversion or educational graph validation has run. [Schema](DATABASE_SCHEMA.md), [AI](AI_MODEL_ORCHESTRATION.md), [technical proposals](TECHNICAL_DESIGN_PROPOSALS.md).
