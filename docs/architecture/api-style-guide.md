# API Style Guide

> Status: **Draft for owner review** · Decision: [ADR-0006](./adr/0006-api-first-multi-client.md).
> Inspired by Google AIP, Microsoft REST API Guidelines and Zalando RESTful API Guidelines, simplified for this project.

## 1. Basics

- One backend API for **all** clients (faculty web now; student, exam, partner apps later).
  The web app has no private back door. It uses the same API as every other client.
- REST over HTTPS, JSON (UTF-8). Base path **`/api/v1`**. Health endpoints at `/health/*`.
- The contract is the **OpenAPI** document generated from code and committed at `api/openapi.json`.
  Clients use generated SDKs.
- JSON field names: **snake_case**. Enum values: **UPPER_SNAKE_CASE** (`IN_REVIEW`, `SCQ`).
- Paths: plural nouns, kebab-case: `/question-versions/{id}`, `/ai-runs`.

## 2. Resources and identifiers

- Every resource has an internal `id` (UUID). Questions also have a human `code` (8 characters, see ADR-0011).
- Timestamps: RFC 3339 in UTC, e.g. `"2026-10-18T09:30:00Z"`; names end in `_at`.
- Money: `{"amount": "12.50", "currency": "INR"}`. Amounts are decimal strings.
- Absent optional values are `null` in responses (never omitted silently once a field exists).

## 3. Methods

| Purpose | Method & path | Success |
|---|---|---|
| List | `GET /questions?…` | 200 + page |
| Get | `GET /questions/{id}` | 200 |
| Create | `POST /questions` | 201 + `Location` |
| Partial update | `PATCH /question-versions/{id}` | 200 |
| Delete (rare; we archive instead) | `DELETE /…/{id}` | 204 |
| **Domain action** | `POST /question-versions/{id}/publish` | 200 (or 202 if async) |
| Long-running work | `POST /ingestion-jobs` | **202** + job resource with `status_url` |

Lifecycle changes are **explicit actions** (`/submit`, `/return`, `/qc-pass`, `/approve`, `/publish`,
`/archive`). A generic `PATCH {"state": "PUBLISHED"}` is not allowed.

## 4. Lists: pagination, filtering, sorting

- Cursor pagination: `?limit=50&cursor=<opaque>`; default 50, max 100.
- Response shape:
  ```json
  { "data": [ … ], "page": { "next_cursor": "eyJ…", "has_more": true } }
  ```
- Counts are a separate, explicit request or field (`?include=total_count`), because counting can be expensive.
- Filters are named query params from a whitelist: `?subject_id=…&difficulty_min=3&state=PUBLISHED`.
  Free text: `?q=…`.
- Sorting: `?sort=-updated_at,code` (`-` = descending); only whitelisted fields.

## 5. Errors

Every error uses one envelope:

```json
{
  "error": {
    "code": "QUESTION_NOT_EDITABLE",
    "message": "Published versions cannot be changed. Start a correction version instead.",
    "request_id": "req_01J…",
    "fields": [ { "path": "answer.value", "code": "TWO_DECIMAL_PLACES_REQUIRED" } ],
    "details": {}
  }
}
```

| Status | When |
|---|---|
| 400 | Malformed request (bad JSON, wrong types) |
| 401 | Not authenticated |
| 403 | Authenticated but lacks the grant/role |
| 404 | Not found **or belongs to another coaching** (never reveal existence) |
| 409 | State conflict (wrong lifecycle state, duplicate, idempotency payload mismatch) |
| 412 | `If-Match` ETag is stale (someone else changed it) |
| 422 | Valid JSON but fails business validation |
| 428 | `If-Match` required but missing |
| 429 | Rate limited (`Retry-After` header) |
| 500/503 | Server fault / temporarily unavailable; safe message only |

`code` values are stable and documented. Clients branch on `code`, never on `message`.

## 6. Concurrency and retries

- Editable resources return an **`ETag`** (e.g. `"rev-12"`). Mutations send **`If-Match`**; stale → 412.
- Create/generate/upload-complete/copy actions accept **`Idempotency-Key`** (client-generated UUID).
  Same key + same body → same result; same key + different body → 409.
- Clients may retry safely on network errors and 503 when they use idempotency keys.

## 7. Authentication & tenant context (multi-client)

| Client | How it authenticates | Phase |
|---|---|---|
| Faculty/admin web | Session cookie `qb_session` (HttpOnly, Secure, SameSite=Lax) + CSRF header `X-CSRF-Token` on mutations | P1 |
| Student/exam mobile apps | OAuth2/OIDC Authorization Code + **PKCE** → short-lived **Bearer** access token + refresh token | P4 |
| Partner systems | OAuth2 client credentials with scopes | Later |

All three resolve to the same internal **Principal** (user or client, coaching, roles, grants). Business code
only sees the Principal, never cookies or tokens.

- The coaching (tenant) comes from the Principal. Clients never send an organization ID to choose a tenant.
- **Origin allow-list** (owner decision, 19 Oct 2026): a change (POST/PUT/PATCH/DELETE) whose `Origin`
  header, or `Referer` when `Origin` is missing, names a web address outside `ALLOWED_ORIGINS` is refused
  with `403 ORIGIN_NOT_ALLOWED` before any handler runs. Requests with neither header (apps, partners,
  scripts) continue to normal authentication. This adds to SameSite cookies, the CSRF header, JSON-only
  bodies and the absence of CORS permissions; it also blocks "login CSRF".
- **Platform admins** choose a coaching to act in via `POST /api/v1/platform/acting-organization`; it's stored
  in their session, shown in the UI, and recorded in every audit event.

## 8. Versioning and change policy

- **Non-breaking** changes are allowed within v1: new endpoints, new optional request fields, new response
  fields, new enum values *only where documented as extensible*.
- **Breaking** changes (removing/renaming fields, changing types or meaning, new required inputs, stricter
  validation of existing input) require **`/api/v2`** or a new endpoint. CI blocks them in v1.
- Deprecation: mark in OpenAPI, send `Deprecation` and `Sunset` headers, keep at least 6 months for external
  clients (internal web app migrates in the same PR).
- Clients must ignore unknown response fields.

## 9. Rate limits and sizes

- Login/OTP/reset endpoints: strict per-IP and per-account limits.
- General: per-principal limits; 429 + `Retry-After`.
- Request body limit 1 MB except uploads. Uploads go through a dedicated upload endpoint (streamed, size-checked).

## 10. Documentation

- Every endpoint has a summary, description, tags (= module), request/response examples and listed error codes.
- Error codes catalogue: `docs/architecture/error-codes.md` (grows with the API).
