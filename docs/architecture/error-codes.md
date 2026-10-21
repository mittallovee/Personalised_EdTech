# API Error Codes

Every error response uses the envelope in the [API style guide §5](./api-style-guide.md#5-errors).
Clients branch on `code`, never on `message`. Codes are stable: once published, a code keeps its meaning.

| Code | HTTP | Meaning | Since |
|---|---|---|---|
| `MALFORMED_REQUEST` | 400 | Body/query/path has the wrong shape or type; `fields` lists each problem | M1 |
| `UNAUTHENTICATED` | 401 | Not signed in, or the session expired | M1 |
| `PERMISSION_DENIED` | 403 | Signed in but missing the role or grant | M1 |
| `NOT_FOUND` | 404 | Does not exist, **or belongs to another coaching** (never revealed) | M1 |
| `CONFLICT` | 409 | Request conflicts with the current state (more specific codes preferred) | M1 |
| `VALIDATION_FAILED` | 422 | Well-formed but breaks a business rule (more specific codes preferred) | M1 |
| `INTERNAL_ERROR` | 500 | Unexpected server fault; details are only in server logs (search by `request_id`) | M1 |
| `ORIGIN_NOT_ALLOWED` | 403 | A change (POST/PUT/PATCH/DELETE) came from a browser on a web address not in `ALLOWED_ORIGINS` | M1 |
| `CSRF_TOKEN_INVALID` | 403 | A change was sent without the `X-CSRF-Token` header from sign-in | M1 |
| `EMAIL_TAKEN` | 409 | An account with this email already exists | M1 |
| `IDEMPOTENCY_KEY_REUSED` | 409 | The `Idempotency-Key` was already used with a different request body | M1 |
| `REVISION_STALE` | 412 | `If-Match` names an older revision: someone else changed it since your read; `details.current_etag` has the current one | M2 |
| `IF_MATCH_REQUIRED` | 428 | A change to an editable resource was sent without `If-Match` (the ETag from your last read) | M2 |
| `LINK_INVALID` | 401 | An activation or reset link is unknown, used, replaced, expired, or its membership or coaching is no longer active (one message for all cases) | M2 |
| `ALREADY_ACTIVATED` | 409 | An activation link was asked for an account that is already active: make a reset link instead | M2 |
| `NOT_ACTIVATED` | 409 | A reset link was asked for an account that was never activated: make a new activation link instead | M2 |
| `ACCOUNT_DISABLED` | 409 | The account is disabled, so no activation or reset link can be made for it | M2 |
| `MEMBER_REMOVED` | 409 | The person is no longer a member of the coaching | M2 |
| `RATE_LIMITED` | 429 | Too many attempts (e.g. sign-in); wait `Retry-After` seconds | M1 |
| `HTTP_<status>` | any | Generic framework error without a specific code (e.g. `HTTP_405`) | M1 |

Feature modules add specific codes here (e.g. `QUESTION_NOT_EDITABLE`, `TWO_DECIMAL_PLACES_REQUIRED`) in the
same pull request that introduces them.
