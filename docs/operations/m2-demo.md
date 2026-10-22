# M2 demo: check identity and coaching admin yourself

M2 ("Identity & coaching admin") is done when the [phase plan](../product/02-phase-plan.md) exit criteria
hold: **role and grant tests pass, and a removed user loses access immediately.** This page shows how to
see both on your PC, then walks through everything M2 can do in about 30 minutes. Setup is in the
[README](../../README.md#run-it-locally-windows-pc-with-docker-desktop); the design is in the
[M2 design note](../architecture/m2-design-note.md).

You need two browser sessions that do not share sign-ins. Use one normal window and one **private
(incognito) window**. For a third person, use a second browser (for example Edge next to Chrome).

## 0. Start fresh

```bash
docker compose up --build -d
docker compose run --rm migrate qbank create-platform-admin --email you@example.com --name "Your Name"
```
(Skip the second line if you already created your platform admin in M1.) Use made-up names and
`@example.com` emails below. Never type real coaching data while testing.

## 1. Create a coaching and activate its Owner (A-04, A-05)

*Normal window, signed in as the platform admin.*

| Step | Expected |
|---|---|
| Open http://localhost:3000/platform/coachings | The **Coachings** list (empty or with earlier test coachings) |
| Fill in the coaching name, the Owner's name and email, then press **Create coaching and make the Owner's link** | The coaching appears as **Active**. A box shows the Owner's activation link **once**, with a **Copy** button |
| Copy the link. Open it in the **private window** | **Set your password**; choose one of at least 12 characters, twice, then **Save and sign in** |
| | You land on Home as "Welcome, <Owner name>"; the top bar shows the **coaching's name** |
| Open the same link again in another private window, type a password (12 or more characters) twice and press **Save and sign in** | The page shows the form first, because it only asks the server when you submit. The server then refuses: "This link is not valid any more. Ask your coaching admin for a new one." (a link works once) |

## 2. Invite people and give grants (B-05, grants)

*Private window, signed in as the Owner.*

| Step | Expected |
|---|---|
| Menu → **Users & grants** | The member list with only the Owner, who has no buttons of their own |
| **Invite someone**: name, email, role Faculty → **Invite and make link** | The person is listed as **Invited**, with **No grants**, and their link is shown once |
| Open that link in a second browser; set a password | They are signed in as faculty. They have **no** "Users & grants" menu item; opening `/admin/users` says "You don't have access" |
| Back as Owner: **Edit grants** for that person, tick **Quality check** and **Approve**, **Save grants** | The list shows "Grants: Approve, Quality check" |
| **Password-reset link** for that person | A link is shown once (valid 1 hour). Opening it lets them choose a new password and ends their old sign-ins |

## 3. Roles, removal and ownership (B-08, B-09)

| Step | Expected |
|---|---|
| **Make admin** on the faculty person, confirm (the screen warns that their grants are cleared, because an admin holds every grant) | They become Admin and the list says "Holds every grant". Their open session sees the change at once, without signing in again |
| **Make faculty**, confirm | Back to Faculty, "No grants" |
| **Remove**, confirm ("Their access ends at once") | They disappear from the list; their history stays in the audit log |
| **The key check: removed means out, immediately.** Keep the removed person's browser open and reload any page | They are sent to the sign-in page at once, not at some later time |
| Invite an Admin, let them activate, then **Make owner** on them and confirm | "<Name> is now the Owner. You are an admin." The new Owner can now manage you (make owner, remove) |

## 4. Platform admin controls (A-06, A-07)

*Normal window, platform admin.*

| Step | Expected |
|---|---|
| **Rename or change time zone** on the coaching | The new name appears for its people, including in the top bar |
| **Suspend**, confirm | The coaching shows **Suspended**. Its people are signed out and cannot sign in or use links. Their data is kept |
| **Reactivate** | They can sign in again (with their password; old sign-ins stay ended) |
| **Act in** the coaching | A coloured banner "Acting in <coaching>" shows on every page; **Users & grants** and **Audit log** now show that coaching. **Stop acting** removes it |

## 5. The audit log (I-03)

Menu → **Audit log** (Owner, admins, or the platform admin acting in a coaching). Every step above is
there, newest first: who did it, when, and what it was before and after. Try the **Kind** and date
filters, and the **Only this person** / **Only this record** buttons. Passwords, tokens and link
secrets never appear.

## 6. Sign in with Google (B-02, B-04), optional

Off until you do the one-time setup in [google-login.md](./google-login.md) (about 15 minutes while
testing with your own account). Without it, the app works with passwords and no Google button shows.
Once set up: link Google from **Profile**, sign out, **Sign in with Google**; or choose **Continue with
Google instead** on an activation page. A Google account is recognised by Google's account ID, never by
email, and signing in with Google never creates an account.

## 7. Prove it with the automated tests

Open the latest pull request on GitHub → **Checks**. All seven must be green:

| Check | What it proves for M2 |
|---|---|
| Backend (lint, types, tests) | The permission table (who may do what, T13); a removed person's existing sign-in gets 401 on the next request (T14); two simultaneous ownership transfers leave one Owner (T15); one email is one person, links are single-use and expire (T16); stale screens are refused (T17); coaching A can never see coaching B's grants, links or Google accounts (T18); the Google rules (T19); one audit event per change (T20); suspending a coaching ends its sessions (T21); retries are safe (T22). The count is about 420 tests |
| Browser tests (e2e) | A real browser does every journey on this page, about 55 of them |
| Web (lint, types, build) | The screens type-check and build; the generated API client matches the contract |
| API contract (no breaking changes) | No change breaks apps already using the API |
| Secret scan | No passwords or keys were committed |
| Python dependencies (pip-audit), Web dependencies (pnpm audit) | No known-vulnerable libraries |

To run them on your PC instead, see [apps/e2e/README.md](../../apps/e2e/README.md) and
`make check` in the README.

## What M2 does not have

- Self-service password reset, one-time codes by SMS or email, and two-factor sign-in (Phase 2).
- Sending links by email: the admin copies and shares them (decided 20 Oct).
- A coaching logo (A-04 part): moved to M6, when file uploads and their safety checks exist.
- Marking, in the members list, who can sign in with Google only.
- Questions, review, AI: M3 onward. The grey menu items are placeholders.

## If something goes wrong

| Symptom | Fix |
|---|---|
| "Too many attempts" | The API limits sign-in and link attempts per address; wait a few minutes (or see the 429 note in the e2e README) |
| "This link is not valid any more" | It was already used, replaced by a newer one, older than 24 hours (reset links: 1 hour), or the person was removed. Make a new one with **Users & grants** |
| The private window shares your sign-in | Close all private windows, then open one fresh, or use a second browser |
| Anything else | `docker compose ps`, `docker compose logs --tail 100 api`, and send the output |
