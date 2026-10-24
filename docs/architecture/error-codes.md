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
| `ROLE_CHANGED` | 409 | The person's role is not the one the request named (`details.current_role`); reload before changing them | M2 |
| `LAST_OWNER` | 409 | The Owner can't be demoted or removed; transfer ownership to an admin first | M2 |
| `OWNER_CHANGED` | 409 | An ownership transfer named an Owner who no longer holds that role; reload before transferring | M2 |
| `INVALID_NEW_OWNER` | 409 | Ownership can only go to an admin of the coaching who is active and has activated their account | M2 |
| `NOT_FACULTY` | 409 | Grants were set for an Owner or admin, who already hold every grant | M2 |
| `MEMBER_REMOVED` | 409 | The person is no longer a member of the coaching | M2 |
| `GOOGLE_DISABLED` | 404 | Sign in with Google is not set up on this server (`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`) | M2 |
| `RETURN_ORIGIN_NOT_ALLOWED` | 422 | The `return_origin` sent to start a Google flow is not in `ALLOWED_ORIGINS` | M2 |
| `PASSWORD_INCORRECT` | 403 | The password sent with a request to link Google is wrong (or the account is locked); counts towards the sign-in lockout | M2 |
| `ALREADY_LINKED` | 409 | A Google account is already linked to this account; unlink it first to link another | M2 |
| `NO_OTHER_LOGIN_METHOD` | 409 | Google can't be unlinked because it is the only way to sign in; the account needs a password first | M2 |
| `GOOGLE_NOT_LINKED` | 404 | There is no linked Google account to unlink | M2 |
| `HIERARCHY_INVALID` | 422 | A syllabus item was given the wrong kind of parent: a subject goes under a class, a chapter under a subject, a topic under a chapter, a subtopic under a topic, and a class has none. A concept goes under a subject | M3 |
| `DUPLICATE_NAME` | 409 | Another syllabus item under the same parent, or another exam, or another source of the same kind, already has this name; or a concept's name or alias is already the name or alias of another concept in the subject (compared without regard to case or spacing) | M3 |
| `PARENT_DEPRECATED` | 409 | The parent item is retired: nothing new goes under it, and an item under it cannot be restored until the parent is | M3 |
| `NAME_TOO_LONG` | 422 | A name (or alias) is too long once its special characters are written out in full for comparing names (for example a ligature becomes three letters) | M3 |
| `IMPORT_INVALID` | 422 | A syllabus import file cannot be read at all: too large, not a spreadsheet or UTF-8 CSV, formulas, unknown or missing columns, too many rows or cells, damaged. Also when applying: a row is an error, there is nothing to import, or more than 5,000 rows would be added or changed at once. (Problem *rows* are not an error when previewing: the preview lists them) | M3 |
| `IMPORT_STALE` | 409 | The syllabus changed after an import preview was made (or something it would add appeared meanwhile), so it was not applied; upload the file again | M3 |
| `RATE_LIMITED` | 429 | Too many attempts (e.g. sign-in), too many syllabus import uploads in a short time, or the server is busy reading other import files; wait `Retry-After` seconds | M1 |
| `HTTP_<status>` | any | Generic framework error without a specific code (e.g. `HTTP_405`) | M1 |

Feature modules add specific codes here (e.g. `QUESTION_NOT_EDITABLE`, `TWO_DECIMAL_PLACES_REQUIRED`) in the
same pull request that introduces them.
