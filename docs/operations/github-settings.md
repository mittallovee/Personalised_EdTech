# GitHub settings checklist (K-05)

> **Status: applied by the owner on 1 Nov 2026.** Checked from the repository API the same day: ruleset
> `protect-main` is active (no deletion, no force-push, pull request required with conversation resolution,
> the eight status checks below required and branches kept up to date), auto-merge is allowed, and secret
> scanning with push protection is on. Re-check after any change to a CI job name: a renamed check that the
> ruleset still waits for blocks every merge.

The repository's rules are only as strong as the settings that enforce them. Everything in this document is a
**setting on github.com that only you (the repository owner) can change**: the AI session that writes the code can
read and push to branches, but it cannot see or change these settings, so nothing here has been applied for you. Work
through the list once (about 15 minutes), tick each box, and tell Claude "settings done" so the project plan can
record it. Do it before the first real coaching data goes into the app (M4).

Why it matters, in one paragraph: today a mistake or a compromised token could push straight to `main`, rewrite its
history, or merge a change whose tests were red, and nothing would stop it. With these settings, `main` only changes
through a pull request whose automatic checks have passed, history cannot be rewritten, and GitHub itself stops a
secret (a password or API key) from being pushed.

> **Where to click.** All of this is under the repository's **Settings** tab (you need the Owner or Admin role). The
> names of GitHub's menus change now and then; if a name below is not there, search the Settings page for the quoted
> words.

## 1. Protect `main` (a "ruleset")

Settings → **Rules** → **Rulesets** → **New ruleset** → **New branch ruleset**.
Name it `protect-main`, set **Enforcement status** to **Active**, and **Target branches** to **Include default
branch** (that is `main`). Then switch on:

- [ ] **Restrict deletions**: `main` can never be deleted.
- [ ] **Block force pushes**: nobody can rewrite the history of `main`. (This is the "no force-push to `main`" rule.)
- [ ] **Require a pull request before merging**: nothing reaches `main` except through a pull request.
  - Leave **Required approvals** at **0**. You are the only person on the repository, and GitHub does not let you
    approve your own pull request, so requiring one approval would lock you out of merging. Review is done by Codex
    and by you reading the summary; the checks below are the hard gate.
  - Switch on **Require conversation resolution before merging**, so a review thread (for example from Codex) has to
    be answered or resolved before the merge button works.
- [ ] **Require status checks to pass**, and add these eight checks (type each name in the search box; they appear
  once the check has run on any pull request):

  | Check name (exactly as GitHub shows it) | What it proves |
  |---|---|
  | `Backend (lint, types, tests)` | Python style, types, import rules and all backend tests, including the restore drill |
  | `Web (lint, types, build)` | The web app compiles; the generated API client matches the API |
  | `Browser tests (e2e)` | What a person does in a real browser against the whole running app |
  | `API contract (no breaking changes)` | The API did not change in a way that breaks existing callers |
  | `Secret scan` | No password or key was committed |
  | `Python dependencies (pip-audit)` | No Python library with a known vulnerability |
  | `Web dependencies (pnpm audit)` | No web library with a known vulnerability |
  | `Code scanning (Semgrep)` | Our own security rules (tenant isolation, SQL, secrets in logs, ...) |

  Also switch on **Require branches to be up to date before merging**. It makes GitHub re-run the checks if `main`
  moved since the last run, so two pull requests that are each fine alone cannot break `main` together. The cost is
  one extra "Update branch" click now and then.
- [ ] Leave **Require linear history** **off**: the project merges with ordinary merge commits.
- [ ] **Bypass list**: leave it **empty**, so the rules also apply to you. (If one day you must override in an
  emergency, you can edit the ruleset first. That is deliberate friction.)

Save with **Create**.

## 2. Secret scanning and dependency alerts

Settings → **Code security** (older name: "Code security and analysis"). Switch on:

- [ ] **Dependency graph** (needed by the next two).
- [ ] **Dependabot alerts**: GitHub tells you when a library we use has a known vulnerability.
- [ ] **Dependabot security updates**: GitHub opens a pull request that fixes such a library (the weekly version
  updates are already set up in `.github/dependabot.yml`, K-01).
- [ ] **Secret scanning**: GitHub looks for known kinds of keys and tokens in the repository.
- [ ] **Push protection** (under Secret scanning): GitHub **refuses a push that contains a recognised secret**, before
  it ever reaches the repository. This is the strongest of the three; the `Secret scan` check above only notices
  afterwards.
- [ ] **Private vulnerability reporting** (optional): lets a researcher report a security problem to you privately.

Some of these may already be on, or may be unavailable on a private repository on a free plan. If a switch is missing
or asks for a paid plan, note it in the "Result" table at the end and tell Claude; the project does not depend on it
(CodeQL, for example, is deliberately not used for that reason).

## 3. Actions (the automatic checks themselves)

Settings → **Actions** → **General**:

- [ ] **Workflow permissions**: choose **Read repository contents and packages permissions**, and leave **Allow
  GitHub Actions to create and approve pull requests** **off**. The workflows already ask for the least they need;
  this makes read-only the default for any future one.
- [ ] **Fork pull request workflows**: choose **Require approval for all external contributors**, so a stranger's pull
  request cannot run code with the repository's permissions until you look at it.
- [ ] **Actions permissions**: keep **Allow all actions and reusable workflows**, and tick **Require actions to be
  pinned to a full-length commit SHA**. The workflows already pin every third-party action to an exact commit
  (Dependabot keeps them current), so this setting only makes GitHub enforce what is already true.
  - *Do not* switch to "Allow \<you\>, and select non-owner, actions" unless you also list every third-party action
    the workflows use, or the checks stop running and every pull request is blocked. Today they are
    `astral-sh/setup-uv`, `gitleaks/gitleaks-action` and `pnpm/action-setup` (GitHub's own `actions/*` are covered by
    "Allow actions created by GitHub"). Each new third-party action added later would need adding to that list too.

## 4. Your account

- [ ] **Two-factor authentication** is on for your GitHub account (Settings → Password and authentication). A
  passkey or authenticator app is better than SMS. Whoever controls this account controls the repository.
- [ ] Review **Settings → Applications → Authorized/Installed GitHub Apps** once: only the apps you recognise (Claude,
  Codex, Dependabot) should have access to this repository.

## 5. Check that it works

- [ ] Open any pull request while its checks are still running: the merge button should say that required checks
  have not passed, and be disabled. (If the checks are all green it will be enabled; that is correct.)
- [ ] On the ruleset page, **Insights** shows rule evaluations; after a few pull requests it should show them passing,
  and nothing "bypassed".
- [ ] (Optional, only if you are comfortable with Git) in a clone of the repository, try `git push origin HEAD:main`
  with some local commit: GitHub must **reject** it, saying changes must be made through a pull request. Do not do
  this if you left a bypass entry for yourself; the push would then succeed.

## Result (fill in, then tell Claude)

| Item | Done? | Notes (for example "not available on my plan") |
|---|---|---|
| 1. `protect-main` ruleset active, eight checks required | | |
| 2. Secret scanning + push protection | | |
| 2. Dependabot alerts + security updates | | |
| 3. Actions permissions | | |
| 4. Two-factor authentication | | |
| 5. Merge button blocked while checks run | | |

## Things this document does not do

- It does not change any setting. Only you can.
- It cannot detect later drift (for example a setting switched off by accident). Look at the ruleset's **Insights**
  now and then, and re-read this list when the team grows, when real coaching data arrives (M4), and when the
  hosting moves to the cloud (M7): at that point cloud accounts need their own checklist.
- Adding a second developer changes item 1: set **Required approvals** to 1 and keep CODEOWNERS (`.github/CODEOWNERS`)
  so a change needs the owner's review.
