# ADR-0015: One-time account links and verified login-method linking
- Status: Proposed · Date: 2026-10-20 · Milestone M2

## Context
People join a coaching by invitation and, in Phase 1, the app sends no email or SMS (B-05, B-06). Admins
need a way to let a new person set up their account and to let someone who forgot their password back in.
Google login (B-02) must never take over an account just because the email address matches (B-04).

## Decision
- **Account links.** An authorised admin creates an activation or reset link for one member.
  - The API returns the secret token once and stores only its SHA-256 hash.
  - The link puts the token after `#`, so browsers do not send it to servers or keep it in logs, and the
    page posts it to the API.
  - Links are single-use. Activation links expire after 24 h, reset links after 1 h.
  - A new link revokes the previous one, and removal or suspension makes every link unusable.
  - Redemption runs in a narrow `SECURITY DEFINER` function, so the runtime role still has no access to
    `password_credentials`. It re-checks that the membership and the coaching are active, sets the
    password and marks the link used in one transaction. A reset also ends the person's sessions.
- **Google (OpenID Connect).**
  - The flow is authorization code with PKCE, `state` and `nonce`, using Authlib, with the pending flow
    bound to a short-lived HttpOnly cookie.
  - Accounts are matched only by `(provider, subject)` in `external_identities`. A sign-in with no linked
    account fails; it never creates or merges an account.
  - Google is linked only by someone who already proves control of the account: while redeeming an
    activation link, or while signed in by typing their current password into the link request itself
    (session age is never proof).
  - Each account has at most one Google account (unique `(user_id, provider)` as well as
    `(provider, subject)`).
  - A login method can be removed only if another one remains.
  - The flow starts with a POST, and the pending flow is stored server-side and used once. For an
    activation, the link token is checked before leaving for Google, and the link's ID travels inside
    the pending flow, never in a URL.
  - The callback re-checks all authority in the transaction that makes the change: the session, user,
    membership, coaching and (for activation) the link. Removal or suspension while at Google stops it.
  - The redirect address is built from a `return_origin` that must be listed in `ALLOWED_ORIGINS`.
- **Retries.** The secret is never stored, so a repeated "create" (same `Idempotency-Key`) cannot replay
  it. Instead it returns the same member with a fresh link and revokes the unseen one. Link redemption is
  for signed-out people: no session or CSRF token, but the Origin allow-list, rate limits and the one-time
  token apply.
- **Emails.** Each normalised email is reserved once platform-wide (`account_emails`, primary key) in the
  same transaction that creates the invitation, so concurrent invitations can't create two accounts for
  one person (B-07), whichever login method activates them.
- No new authority comes from a link or from Google: both end in the same session and Principal as a
  password login (ADR-0006), with membership and grants loaded from the database on every request.

## Consequences
+ No email or SMS provider is needed in Phase 1; adding delivery later reuses the same links.
+ A leaked database copy reveals no usable links; a stale or shared link stops working after one use.
− Admins must pass links on themselves (e.g. WhatsApp). The 24 h and 1 h limits keep a forwarded link
  from staying useful for long.
− Google login needs a one-time Google Cloud setup (client ID and secret per deployment).

## Alternatives
- Email the links (needs a mail provider and contradicts the Phase 1 "no notification email" policy).
- Temporary passwords set by admins (admins would know users' passwords, and they get reused).
- Match Google accounts by verified email (simple, but lets anyone who controls that address take over the
  account, against B-04).
