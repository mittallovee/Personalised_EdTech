# M1 demo: check the foundation yourself

M1 ("walking skeleton": the thinnest version of every layer, wired end to end) is done when the
[phase plan](../product/02-phase-plan.md) exit criteria hold:
**CI green; two-coaching isolation tests pass; restart keeps data.** This page shows how to see each one
on your PC in about 15 minutes. Setup steps are in the [README](../../README.md#run-it-locally-windows-pc-with-docker-desktop).

## 1. Start the app and sign in
```bash
docker compose up --build -d
docker compose run --rm migrate qbank create-platform-admin --email you@example.com --name "Your Name"
```
| Step | Expected |
|---|---|
| Open http://localhost:3000 | You are sent to the sign-in page |
| Sign in with a wrong password | One generic message, never "no such user" (B-01) |
| Sign in correctly | Home shows your name, "Platform admin" and System health: API, database, migrations all `ok` |
| **Sign out** | Back on the sign-in page; going to http://localhost:3000 sends you to sign-in again |
| Last (optional): five wrong passwords in a row | The account locks for 15 minutes, even for the right password (B-01). Do this after step 2, or wait out the lock |

## 2. Restart keeps data (test T10)
```bash
QBANK_CHECK_EMAIL=you@example.com make restart-check     # asks for your password
```
The [script](../../infra/scripts/restart-check.sh) signs in, runs `docker compose down` then `up`, waits
for the app, and checks that the same sign-in still works. It ends with `PASS: …`; anything else prints
`FAIL:` and the reason. Afterwards, sign in again in the browser to see your account is still there.

> `docker compose down -v` (with **-v**) deletes the database volume, i.e. all data. Never use it unless
> you mean to start from empty.

## 3. Tenant isolation and the rest of CI
Open the latest pull request on GitHub → **Checks**. All four must be green:

| Check | What it proves |
|---|---|
| Backend (lint, types, tests) | Lint, types, import rules, and every test, including T1–T4: coaching A can never see, add or change coaching B's rows, even with no coaching selected, and the app's database role cannot switch these rules off (ADR-0005); `api/openapi.json` matches the code (T12) |
| Web (lint, types, build) | The web app is type-checked, tested and builds; its generated API client matches the contract |
| API contract (no breaking changes) | No change to the API breaks apps already using it |
| Secret scan | No passwords or keys were committed |

## 4. Optional: on your own domain
To reach the same app at `https://qb.loveemittal.online`, follow [remote-access.md](./remote-access.md).

## What M1 does not have yet
Creating coachings, inviting faculty, roles and grants (M2); questions (M3 onward); AI (M5). The grey
menu items (Questions, Review, Taxonomy, AI & prompts, Admin) are placeholders for those.

## If something goes wrong
| Symptom | Fix |
|---|---|
| `port is already allocated` | Another program uses port 3000, 8000 or 5432: close it, or stop the other stack |
| Home says "Cannot reach the server" | `docker compose ps`: all services should be running; see `docker compose logs api` |
| Locked out after wrong passwords | Wait 15 minutes. Self-service password reset comes in Phase 2 |
| Check fails with `FAIL:` | The message says which step; send it with `docker compose logs --tail 100` |
