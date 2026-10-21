# Browser tests (Playwright)

A real Chromium browser opens the app and clicks through it the way a person would: sign in, see
Home, sign out, activate a new coaching's Owner account. The tests talk to the **running stack**, so
they also check that the web app, API and database work together.

CI runs them on every pull request (job "Browser tests (e2e)"). If one fails, the job keeps a report
with screenshots and a trace (a step-by-step recording); download `playwright-report` from the run's
Summary page and open `index.html`.

## Run them on your PC

```bash
docker compose up --build -d                                  # the app on http://localhost:3000
pnpm install                                                  # once
pnpm --filter @qbank/e2e exec playwright install chromium     # once: downloads the browser
E2E_ADMIN_EMAIL=you@example.com E2E_ADMIN_PASSWORD='your admin password' \
  pnpm --filter @qbank/e2e e2e
```

- `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD`: a platform admin (README, "Create your platform admin
  account"). The tests create a new coaching each run, with a unique name, in that database.
  Use a local or test database, never a real one.
- `E2E_BASE_URL`: another address (default `http://localhost:3000`).
- To watch the browser: add `--headed`; to step through one test: `--debug`;
  to open a failure report: `pnpm --filter @qbank/e2e exec playwright show-report`.

## Writing a test

- One file per journey in `tests/`, named after what the person does (`activation.spec.ts`).
- Find elements the way a person does: by role and visible text (`getByRole("heading", …)`).
- Set up data through the API (`tests/helpers.ts`), not by clicking through unrelated screens.
- Use synthetic data only; never real coaching content.
