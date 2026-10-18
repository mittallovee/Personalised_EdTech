# API Contracts — Proposed Review Baseline

18 October 2026. Concrete route/payload proposal, not deployed endpoints or final generated OpenAPI.

## Shared protocol

/api/v1 business prefix; JSON UTF-8, UUID resource IDs and RFC3339 UTC timestamps. Normal session resolves one coaching; platform-only routes name explicit target coaching. A browser-supplied organization_id never grants access.

Opaque server session cookies with CSRF protection are proposed. Lists use opaque stable cursors, default 50/max 100 items; filters whitelist language/type/class/subject/chapter/topic/concepts/difficulty/workflow/archive/PYQ. Counts and graph links use the identical coaching/filter scope.

Editable resources expose an ETag such as "revision:12". Mutations require If-Match; missing precondition returns 428, stale precondition 412, state/idempotency conflicts 409, invalid content 422. Authentication failure 401; missing action grant 403; inaccessible foreign resource 404. Errors expose safe field/code/correlation details, never another tenant's names or credentials.

Idempotency-Key is required for create/materialize/generation/copy actions. Scope actor+tenant+operation, bind request hash; same replay returns same resource, changed payload conflicts. Durable output mappings remain through job/copy retries.

## Proposed resources

| Capability | Method / route | Contract |
| --- | --- | --- |
| Health/readiness | GET /health; GET /ready | Minimal status, no tenant data/secrets |
| Login/activation/linking | /auth/login, /auth/google/start and callback, /auth/otp/request and verify, /auth/activate, /auth/methods/link | Alternative verified methods; explicit linkage, rate limits, CSRF/state/nonce where applicable |
| Current identity/logout | GET /me; GET /me/organization; POST /auth/logout | One faculty coaching; current-session logout; no device-list/remote-device routes |
| Coaching/Owner provisioning | POST /platform/coachings | Full platform only, idempotent first Owner setup |
| Branding | PATCH /platform/coachings/{id}/branding | Platform-only, validated logo/name and ETag |
| Faculty/admin management | /memberships; /memberships/{id}/grants; /admins; /ownership-transfer | Current-role target validation; Owner-only peer-admin actions; transfer atomic |
| Upload | POST /uploads; POST /uploads/{id}/complete | Streaming limit/signature/checksum, private handle; upload completion is not extraction success |
| Ingestion submission | POST /ingestion-jobs | upload_ids, idempotency key; 202 durable job |
| Job state/cancel/retry | GET /jobs/{id}; POST /jobs/{id}/cancel or retry | Current actor/role, state/revision; cancel_requested distinct from cancelled |
| Manual/candidate work | POST /candidates; GET/PATCH /candidates/{id} | Save incomplete typed work; auto duplicate check, source/AI evidence |
| Associations | PATCH /ingestion-groups/{id}/associations | Faculty correction with edit scope, revision guard and affected-output findings |
| Duplicate disposition | POST /candidates/{id}/duplicate-disposition | Human exact/variant/translation/unrelated evidence, target revision and authority |
| Materialize | POST /candidates/{id}/materialize | New master/code or exact-source attachment to existing master; replay-safe |
| Bank | GET /questions; GET /questions/{id}; GET /questions/by-code/{code} | Own-coaching complete bank; global uniqueness does not imply public lookup |
| Working version | POST /questions/{id}/versions; PATCH /question-versions/{id} | Correction under same code; append revision, invalidate current eligibility |
| Workflow | POST /question-versions/{id}/submit, return, qc-pass, approve, publish | Exact revision/ETag and separate grant per formal action |
| Archive/restore | POST /questions/{id}/archive or restore | Creator/admin/platform only; no hard-delete history route |
| Catalogue/graph | GET /taxonomy; GET /concepts/graph; GET /concepts/{id}/questions | Bounded same-coaching views; concept assignment includes primary/secondary |
| Taxonomy management | POST/PATCH /taxonomy; /concepts/{id}/approve, merge, revoke; /concept-edges | Admin or authorized internal AI, no ordinary faculty creation |
| Languages | GET/POST /languages | Read catalogue; admin extension |
| Models/credentials | GET /ai/models; /admin/ai/models; /admin/ai/credentials | Enabled compatible catalogue; protected write-only keys/masked status |
| AI operations | POST /ai/runs; GET /ai/runs/{id} | Operation, exact source revision, compatible model/default, budget and per-question consent |
| Admin reports/budgets | /admin/ai/usage; /admin/ai/budgets; /admin/storage | Coaching admin/platform; evidence-labeled usage, protected policies |
| Original source | GET /sources/{id}/view; DELETE /admin/sources/{id} | Faculty view if retained; admin delete receipt preserving derived dependencies |
| Notifications | GET /notifications; POST /notifications/{id}/read | In-app only, current recipient/admin access |
| Dataset copy | POST /platform/dataset-copies; GET /platform/dataset-copies/{id} | Platform-only explicit source/target, consistent manifest, background progress |

Test/export/student/course/live/video routes are later; no placeholder endpoint should falsely advertise support.

## Examples

Accept ingestion:

```json
{
  "upload_ids": ["00000000-0000-4000-8000-000000000101"],
  "client_reference": "physics-batch-1"
}
```

Proposed 202 response:

```json
{
  "job_id": "00000000-0000-4000-8000-000000000201",
  "state": "QUEUED",
  "status_url": "/api/v1/jobs/00000000-0000-4000-8000-000000000201"
}
```

AI mixed-target request:

```json
{
  "operation": "GENERATE_VARIANTS",
  "source_revision_id": "00000000-0000-4000-8000-000000000301",
  "model_catalogue_id": null,
  "targets": [
    {"question_type": "SCQ", "difficulty": 4, "count": 2},
    {"question_type": "NUMERICAL", "difficulty": 7, "count": 1}
  ],
  "instructions": "Keep the primary concept; reduce calculation."
}
```

Null catalogue ID resolves the coaching's compatible default. Record selected and actual fallback choices. Target difficulty is a requested target, not a verified achieved label.

A CHECK_ANSWER request may carry apply_correction=true for exactly one source question/revision. Omitted/false means findings only. The grant is not reused for the next question or expanded to a batch. Published corrections create a working version, never modify the source publication. Protected write authority and current revision are rechecked when results complete.

Proposed safe field error:

```json
{
  "error": {
    "code": "NUMERICAL_PRECISION",
    "message": "Review the answer precision before publication.",
    "fields": [{"path": "answer.value", "code": "TWO_DECIMAL_PLACES_REQUIRED"}],
    "correlation_id": "example-correlation"
  }
}
```

Job detail reports state/stage, completed/total units with an explicit unit, per-file results, retained drafts and safe errors. Unknown totals are null; no invented percent. Terminal states include SUCCEEDED, PARTIAL, FAILED and CANCELLED; retry references the original mapping/checkpoints.

## Contract invariants

Source links, passage/assets/concepts and input revisions must be same-coaching/currently authorized. AI-completion writes reject stale revision/removed authority. Metadata direct fill never bypasses publish validators. Translation source must have completed QC; variants need not.

Copied published snapshots retain imported evidence, new destination master codes and complete dependencies. Copy retries resume immutable mapping, not live synchronization. No credentials/users/grants are imported. No actual API/schema/provider tests have run.

[Question payload examples](QUESTION_SCHEMA_EXAMPLES.md), [database](DATABASE_SCHEMA.md), [workflow](QUESTION_LIFECYCLE_AND_QC.md).
