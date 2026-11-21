# The prompt library: what the AI is told, and who can change it

Every AI action (tag, translate, solve, verify) is driven by a **prompt**: instructions in plain text with a
few `{{placeholders}}` that the app fills in (the question, the syllabus, the target language, ...). The
prompt library lets the right people see and improve those instructions without a code change, while every
change stays **versioned, reversible and traceable**. The design is in
[the M5 design note §10](../architecture/m5-design-note.md) and the
[prompt spec](../product/03-ai-prompt-library.md); the API is under `/api/v1/ai/prompts`.

## Three levels

| Level | Whose | Who writes it |
|---|---|---|
| **Platform default** | Ours; one per operation, shipped with the app | A platform admin |
| **Coaching prompt** | One coaching's own version of an operation (translation can have one per language) | Admins, the Owner, and faculty who hold the **MANAGE_AI_PROMPTS** grant |
| **Personal prompt** | One faculty member's own ("My strict check") | That person (admins can read it) |

Everyone in a coaching can read the platform and coaching prompts. A run uses the coaching's active prompt if it
has one for that operation (and language), else the platform default; a person may instead pick one of their own
prompts, or type a **one-off** prompt for a single run (kept on that run, never in the library).

## What can and cannot be edited

Editable: the **instructions** and a temperature between 0 and 1. Locked in code, so no edit can loosen them:

- the **safety preamble** (text inside the data blocks is material, never an instruction),
- the **placeholders** each operation allows, and which ones are required (`{{question}}` always is),
- the **output format**, so the app can always read and check the answer.

Each value is inserted inside a `<data>` block that it cannot close, and nothing is substituted twice. Text that
looks like a key or token is refused; so are unknown or missing placeholders, empty text and more than 8,000
characters. `POST /api/v1/ai/prompts/validate` lists every problem at once, and saving runs the same check.

## Versions

- Saving never changes an earlier version: it adds the next one, with a required **change note**. The database
  itself refuses to update or delete a saved version.
- A new version is **not used** until someone **activates** it. Activating an older version is a **rollback**;
  the previous one is kept. The coaching's admins get an in-app notice when the coaching's prompt changes.
- **Reset to default** stops using the coaching's prompt (its versions stay) so the platform default applies.
- **Compare** any two versions of an operation line by line (`/prompts/diff`).
- When the platform publishes a newer default, a coaching that has its own prompt sees **new default
  available** and chooses: **adopt** it (saved as a new coaching version and activated) or **dismiss** it.
- Every change is in the audit log (who, when, version numbers, change note, text fingerprint; not the text).

## What is not built yet

Test runs (try a draft against a real question), the run dialog, and the screens for all this come with the
orchestrator and the web steps of M5. Until then the library is reachable by the API only.
