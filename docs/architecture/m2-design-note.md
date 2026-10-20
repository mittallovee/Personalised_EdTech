# M2 Design Note — Identity & coaching admin

> Status: **Draft for owner approval** · Milestone M2 of Phase 1 ([phase plan](../product/02-phase-plan.md))
> Requirements: A-04, A-05, A-06, A-07, B-02, B-04, B-05, B-06, B-08, B-09, B-10, I-03 (and grants from §2 of the
> requirements) · ADRs 0005, 0006, 0014, **0015 (new)** · Builds on the [M1 design note](./m1-design-note.md)

## 1. Goal

Turn the M1 skeleton into a usable multi-coaching identity system: you create a coaching and its Owner, the
Owner activates their account and invites admins and faculty, admins give grants, and every one of those
changes is audited. Removing someone takes their access away **on their very next request**.

Owner decisions this note follows (20 Oct 2026, "use your recommendations"):
1. **Activation and reset links are copied and shared by the admin** (WhatsApp, etc.); the app sends no
   email (already B-05/B-06). Email delivery can be added later without changing the link design.
2. **Google login stays in M2**, as its last feature PR, with a step-by-step setup guide for the Google Cloud
   console. Everything before it works with email + password only.

## 2. What you will be able to do at the end of M2

1. As platform admin: create a coaching (name, timezone) and its Owner; copy the Owner's activation link.
2. Open that link (e.g. in a private window), set a password: you are signed in as the Owner, and the top bar
   shows the coaching's name (A-05).
3. As Owner: invite an admin and a faculty member, give the faculty member grants (e.g. QC), promote or
   demote, remove someone, transfer ownership to another admin, and generate a password-reset link.
4. As platform admin: suspend and reactivate a coaching (A-07); "act in" a coaching with a visible banner (A-06).
5. See every change in the audit log, with who, when, and before/after (I-03).
6. Sign in with Google once you have done the one-time Google setup (B-02), and link Google to an existing
   account only from inside that account (B-04).

## 3. Roles, grants and who may do what

Roles live on the membership: `OWNER`, `ADMIN`, `FACULTY` (exactly one active Owner per coaching). Grants are
extra rights for faculty: `QC`, `APPROVE`, `PUBLISH`, `EDIT_OTHERS`, `MANAGE_AI_PROMPTS`. Owner and admins hold
all grants implicitly. M2 stores and shows grants; question features that check them arrive in M3–M5.

| Action | Faculty | Admin | Owner | Platform admin |
|---|---|---|---|---|
| See the member list | No | Yes | Yes | Any coaching (acting) |
| Invite / remove faculty, set faculty grants, faculty reset link | No | Yes | Yes | Yes |
| Invite admin, promote faculty → admin, demote/remove admin, admin reset link | No | No | Yes | Yes |
| Transfer ownership (to an active admin of the same coaching) | No | No | Yes | Yes |
| Owner's reset link; create coaching + first Owner; rename; suspend/reactivate | No | No | No | Yes |
| See the coaching's audit log | No | Yes | Yes | Yes (+ platform-level events) |

Rules that hold everywhere:
- Permissions are decided on the server from the signed-in **Principal**, which is reloaded from the
  database on every request; nothing a client sends (role, grant, coaching ID) is trusted.
- Every change names the target's **current** role and revision (`If-Match`), so a stale screen can't, for
  example, "remove a faculty member" who was promoted to admin a minute ago (412 or 409 instead).
- Nobody can remove or demote the Owner; the Owner leaves that role only through a transfer.
- One central policy module (`core/permissions.py`) holds these rules, tested as a full table (§9).

## 4. Activation and reset links (ADR-0015)

- An admin's action creates a link and the API returns its secret **once**:
  `https://<app>/activate#<token>`. The token is 32 random bytes; only its SHA-256 hash is stored.
- The part after `#` never leaves the browser in normal page loads or logs; the page sends it to the API in
  a POST body.
- **Activation** links last 24 h (B-05); **reset** links last 1 h; both are single-use. Making a new link for
  the same person revokes the old one; removing a member revokes their links.
- Redeeming checks, in one transaction, that the link is unexpired and unused, and that the person's
  membership and coaching are still active. It then sets the password (Argon2id, min 12 characters) and
  marks the link used. A reset also ends all of that person's sessions. The person is then signed in.
- Redeeming is rate-limited like sign-in. Every error is the same generic "link is invalid or expired".
- **Retries are safe** (style guide §6). Creating a coaching and inviting a member take an
  `Idempotency-Key`: the key and a hash of the body are stored with the created member
  (`idempotency_keys`, migration 0004).
  - Same key + same body: no second member, no `EMAIL_IN_USE`. The response is the same member with a
    **fresh** link, and the unseen first link is revoked. The secret itself is never stored, so it can't
    be replayed; a lost response therefore costs nothing.
  - Same key + different body: `409 IDEMPOTENCY_KEY_REUSED`.
  - "New link" actions need no key: any retry leaves exactly one valid link, the last one shown.
- An invited person who has not activated has no way to sign in and sees no data.

## 5. Google login (B-02, B-04, ADR-0015)

- OpenID Connect "authorization code" flow with PKCE, `state` and `nonce`, via Authlib. The pending flow is
  bound to a short-lived HttpOnly cookie, which stops "login CSRF".
- The flow starts with `POST /api/v1/auth/google/start {purpose, return_origin, link_token?}`, which returns
  the Google address to go to. Being a POST, it passes the Origin check.
  - `return_origin` must be in `ALLOWED_ORIGINS`, so the same setup works on `localhost:3000` and on
    `qb.loveemittal.online`.
  - The API stores the pending flow server-side: a hash of `state`, PKCE verifier, nonce, purpose, and for
    `ACTIVATE` the account link's ID, for `LINK` the signed-in user. It expires after 10 minutes, and its
    random ID goes in the pending cookie.
  - `purpose` is one of three:
    - `SIGN_IN` needs nothing else;
    - `ACTIVATE` needs the activation `link_token`, which the page reads from the `#` part, so the token
      is checked **before** leaving for Google;
    - `LINK` needs a session, the CSRF header and the password re-entered in the last 5 minutes.
  - The callback (`GET /auth/google/callback`) requires the cookie and a matching `state`, uses the pending
    flow once, and verifies Google's ID token (signature, audience, nonce).
    - For `ACTIVATE` it re-checks, in one transaction, that the link is still valid and the membership
      active. It then links the subject (refused if that Google account is linked to someone else), marks
      the link used, activates the user and starts the session.
- An account is found by Google's permanent **subject ID**, never by matching email (B-04). A Google login
  with no linked account fails with a generic message; it never creates an account.
- Ways to link Google (both through the flow above):
  - while activating, choose "Continue with Google" instead of setting a password (`ACTIVATE`);
  - when signed in, use "Link Google account" after re-entering the password (`LINK`).
- You can unlink Google only if a password remains, so nobody locks themselves out.
- The feature is off until `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are set in `.env`. Both stay out of
  git, and the button is hidden while they are unset.

## 6. Database (migrations 0004–0006)

All new coaching-owned tables have `organization_id`, `FORCE ROW LEVEL SECURITY` with the tenant policy, and
composite foreign keys `(organization_id, …)` (ADR-0005). The runtime role still never touches
`password_credentials` directly.

| Migration | Change |
|---|---|
| 0004 | `users.status` gains `INVITED`; `organizations.revision`, `memberships.revision` (for `If-Match`); unique index "one active OWNER per coaching"; `membership_grants (organization_id, membership_id, grant)`; `idempotency_keys (organization_id, key, request_hash, resource_id, created_at)`, kept 24 h |
| 0005 | `account_links (id, organization_id, user_id, purpose ACTIVATION/RESET, email, token_hash, created_by, created_at, expires_at, used_at, revoked_at)` + narrow `SECURITY DEFINER` functions: check email free, redeem link and set password, revoke a member's sessions/links (only for a user in the current coaching), list members' sign-in emails (current coaching only) |
| 0006 | `external_identities (user_id, provider, subject, email_at_link, linked_at)`, unique `(provider, subject)`; `oauth_flows (id, state_hash, code_verifier, nonce, purpose, account_link_id, user_id, return_origin, expires_at, used_at)`; lookup by subject and use of a flow through definer functions |

Every change also writes an `audit_events` row in the same transaction: actor, acting-as-platform flag,
action (e.g. `MEMBER_ROLE_CHANGED`, same style as M1's `USER_SIGNED_OUT`), target, before and after. Tokens, hashes and passwords are never
written to audit events or logs.

## 7. API (all under `/api/v1`)

Changes need a session and the CSRF header, except the endpoints for signed-out people. Those are sign-in,
`POST /auth/links/redeem`, and `POST /auth/google/start` with purpose `SIGN_IN`/`ACTIVATE`. Like M1's
login, they are protected by the Origin allow-list, rate limits, and a one-time secret (the link token or
the OAuth `state` + cookie). The Google callback is a GET from Google: it changes nothing unless the pending
cookie and `state` match.

| Method & path | Purpose |
|---|---|
| `GET /me` | Adds the coaching's name, grants and the acting coaching |
| `GET/POST /platform/organizations` | List coachings · create coaching + first Owner (returns activation link; `Idempotency-Key`) |
| `PATCH /platform/organizations/{id}` | Rename, timezone (`If-Match`) |
| `POST /platform/organizations/{id}/suspend` · `/reactivate` | A-07 |
| `POST/DELETE /platform/acting-organization` | Start/stop acting in a coaching (A-06) |
| `GET /members` · `GET /members/{id}` | Member list (paginated) with role, status, grants, email |
| `POST /members/invitations` | Invite faculty or admin (returns activation link; `Idempotency-Key`) |
| `POST /members/{id}/activation-link` · `/reset-link` | New link (old one revoked) |
| `PUT /members/{id}/grants` | Set faculty grants (`If-Match`) |
| `POST /members/{id}/change-role` · `/remove` | Promote/demote · remove, naming the expected current role |
| `POST /organization/transfer-ownership` | To an active admin; `If-Match` on the coaching |
| `POST /auth/links/redeem` | Activate or reset with a link token (no session; see above) |
| `GET /auth/methods` | Which sign-in methods are on (hides the Google button when off) |
| `POST /auth/google/start` · `GET /auth/google/callback` · `POST /auth/google/unlink` | §5 |
| `GET /audit-events` | Coaching (or platform) audit log, filters: actor, entity, time; paginated |

New error codes are added to `error-codes.md`, for example `LINK_INVALID`, `EMAIL_IN_USE`,
`ROLE_CHANGED` (409), `LAST_OWNER` and `ACTION_NOT_ALLOWED` (403). The contract (`api/openapi.json`) and
the generated client are updated in the same PR as each endpoint.

## 8. Web

| Screen | Content |
|---|---|
| Sign-in | Adds "Sign in with Google" (only when enabled) |
| `/activate` | Set password (twice) or continue with Google; generic error for bad links |
| Top bar | Coaching name; a coloured "Acting in <coaching>, stop" banner for platform admins |
| Admin → Users & grants | List, invite (link shown once with a Copy button), grants, role, remove (with confirmation), reset link |
| Admin → Coaching | Transfer ownership (Owner) |
| Admin → Audit log | Filterable list with before/after |
| Platform → Coachings | List, create coaching + Owner, rename, suspend/reactivate, "Act in" |
| Profile | Link/unlink Google |

The web app has no business rules: the API decides what is allowed and returns which actions are
available, so the screens only show or hide buttons.

## 9. Tests that prove M2

| # | Test | Type |
|---|---|---|
| T13 | Permission table (§3): every action × Faculty/Admin/Owner/Platform/another coaching's admin → allowed or 403/404 | api |
| T14 | **Removed user loses access immediately**: their existing session gets 401 on the next request; links revoked; their audit history and memberships stay | api + integration |
| T15 | Ownership transfer: two concurrent transfers or replays leave exactly one Owner; old Owner becomes admin; Owner can't be removed/demoted | integration |
| T16 | Links: single use, expiry (24 h / 1 h), new link revokes old, no use after removal or suspension, reset ends sessions, token never stored/logged | integration + api |
| T17 | Stale changes: `If-Match` missing → 428, stale → 412; wrong expected role → 409 | api |
| T18 | Isolation (T1–T4 pattern) for `membership_grants`, `account_links`, `external_identities` | integration |
| T19 | Google: match by subject only (same email, different subject → no access); state/nonce/PKCE checked; pending flow single-use and expiring; **activation + Google** binds only the invited user and fails once the link is used, revoked or the member removed; `LINK` needs recent password; unlink needs another method (Google simulated; no real Google call in CI) | api |
| T20 | Every change in §7 writes exactly one audit event with correct actor/before/after and no secrets | api |
| T22 | Retries: invitation / coaching creation with the same `Idempotency-Key` and body → one member, a fresh link, the earlier link revoked; different body → 409; link redemption and the signed-out endpoints work without a session or CSRF token but are refused from a foreign Origin | api |
| T21 | Suspended coaching: members can't sign in or redeem links; data kept; reactivation restores access | api |

## 10. Out of scope for M2

- Email/SMS delivery of links, self-service reset and OTP (P2).
- Two-factor authentication for platform admins (P2, B-12).
- A device list or remote logout of other devices (spec says none).
- Inviting someone who already belongs to another coaching (B-07: one coaching per person; the invite is
  refused with `EMAIL_IN_USE`).
- **Coaching logo** (A-04): moved to M6, when file uploads and their safety checks exist; M2 shows the name.

## 11. Work plan (pull requests)

| PR | Content |
|---|---|
| 1 | This design note + ADR-0015 (docs only) |
| 2 | Permissions core, Principal grants, `GET /audit-events` (recording exists since M1), `/me` additions; migration 0004 |
| 3 | Platform: create coaching + Owner, list, rename, suspend/reactivate, acting-organization; migration 0005 (links) |
| 4 | Link redemption (activation + reset) API and `/activate` page |
| 5 | Members: list, invite, new links, grants; web Users & grants |
| 6 | Change role, remove (T14), transfer ownership (T15); web |
| 7 | Web: platform console, acting banner, audit log page |
| 8 | Google login + linking (migration 0006) + `docs/operations/google-login.md` setup guide |
| 9 | M2 demo notes and exit checks |

## 12. Decisions for the owner

1. Approve this note (merge PR 1), or ask for changes.
2. Agree to move the **coaching logo** to M6 (§10). I recommend yes: uploading images safely needs the file
   checks that M6 builds anyway.
3. Agree to reset links lasting **1 hour** (activation: 24 h, as in B-05). I recommend 1 h because a reset
   link is a key to an existing account.
