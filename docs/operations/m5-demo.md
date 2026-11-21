# M5 demo: try the AI helpers yourself

M5 ("AI assist & prompt library") is done when the [phase plan](../product/02-phase-plan.md) exit criteria
hold: **every run is traced to its model and prompt version, the budget stop works, and no coaching can use
another coaching's key.** This page shows how to see each of those on your PC, then walks through what M5 can
do. Setup is in the [README](../../README.md#run-it-locally-windows-pc-with-docker-desktop); the design is in the
[M5 design note](../architecture/m5-design-note.md) and
[ADR-0009](../architecture/adr/0009-ai-platform.md) / [ADR-0023](../architecture/adr/0023-ai-keys-encryption-and-provider-access.md).

Use made-up questions and `@example.com` emails. **Never paste a real API key into a chat, a file or a message:
a key goes only into the AI page of the app.**

## 0. Two ways to try it

**A. With the built-in stand-in (no key, no bill, no network).** Good for seeing every screen work. Make a master
key once and start the stack with the stand-in on (PowerShell):

```powershell
$env:AI_KEYS_MASTER_KEY = [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
$env:AI_DEMO_PROVIDER = "true"
docker compose up --build -d
```

Then type any made-up text as the OpenAI key (for example `fake-openai-aaaaaaaaaaaaaaaaaaaa`). The stand-in answers
every request sensibly but is not an AI: it tags with the first chapter and concept, solves with the first option,
reports one note when verifying, and "translates" by marking the words. Hosted environments (staging,
production) refuse `AI_DEMO_PROVIDER`.

**B. With a real provider.** Make a real master key (see [AI keys](./ai-keys.md): keep a copy in your password
manager, **separate from your database backups**; without it the stored keys cannot be opened), leave
`AI_DEMO_PROVIDER` off, and paste your provider key on **AI** in the app. The adapters were written from the
providers' documents and are **unverified against the live services** until you run `qbank ai-smoke` once per
provider (see [AI keys](./ai-keys.md)). Set a small budget first.

Set up the coaching as in the [M3 demo](./m3-demo.md): a class, subject, chapter, topic and at least one concept.

## 1. Admin → AI (H-01 to H-06)

Sign in as the Owner and open **AI** in the menu.

| Step | Expected |
|---|---|
| **Provider keys**: type a key for OpenAI, **Save key** | "The OpenAI key is saved." The box empties and only "Stored, ending xxxx" shows. **A key can never be read back**; only replaced or removed |
| **Models**: **Refresh the list** under OpenAI | After a few seconds the list appears (a background job fetches it). A refresh that fails says why in words |
| Tick **Offer <model>** | The model is now available to faculty. A model whose price the provider does not give shows "unknown" and can be given a price under **Prices and Economy** |
| **Rate and monthly budget**: rupees per dollar `83`, default budget `1000` | Saved. Without a rate, budgets are off and the page says so |
| **What each operation uses**: choose the model for tag, translate, solve and verify | Saved. A model turned off later is flagged on its card |

## 2. Run an operation on a question (H-04, H-07 to H-10)

As faculty (or the Owner), open a draft question → the **AI** tab.

| Operation | Expected |
|---|---|
| **Tag a question** | The chapter, topic, main concept, difficulty and Bloom level are chosen from **your coaching's own syllabus** and filled in (they can be changed afterwards). If the question has changed meanwhile the run says "the question changed while this ran" and writes nothing. The subject must be chosen first |
| **Solve a question** | A suggested answer and worked solution, shown beside the current answer. **Nothing changes until you press "Apply the answer and solution"** |
| **Verify a question** | Findings (error, warning, note) as plain text. If the model is sure, a corrected version is shown beside the current one; **"Apply the correction" is a separate click** |
| **Translate a question** | A suggestion first; **"Create the translation"** makes a **new draft question** with its own code, linked to this one. The source is not touched. Later, if the source publishes a newer version, the translation shows **"source updated"** (D-13) |
| Tick **Test only** | The same call and cost, but nothing is ever written to the question |

Each run in **History of this question** shows how it ended, the model that answered (and any fallback), and
whether it was applied. A failed run says why in words; the provider's own text is never shown.

**Prompts (H-13, H-14).** Menu → **Prompt library**: the instructions each operation is given. The platform has a
default; your coaching can write its own (needs the "Manage AI prompts" grant, which the Owner and admins hold),
and anyone can keep prompts of their own and pick one when they run. A saved version never changes; switching
one on, rolling back and resetting are separate, recorded steps. The safety rules and the answer format are
fixed by the system and cannot be edited. The Owner and admins also keep a **translation glossary** (terms to
translate one fixed way).

## 3. Money (H-05, H-06; exit criterion: the budget stop works)

| Step | Expected |
|---|---|
| Menu → **AI usage** | Your use this month in rupees against your budget, with a bar |
| As an admin, lower the default budget to `0.01` (Admin → AI) | A faculty member's next run is **refused before anything is sent**: "This would pass your monthly AI budget." |
| Give one person their own budget on **AI usage** | They use theirs; everyone else keeps the default. "Use the default" removes it |
| Costs | In US dollars (what providers bill) and rupees (at the rate when the run happened). A model with no price is allowed, but its cost is shown as unknown |

The month is the calendar month in India time and starts again on the 1st. The ledger only ever grows: a mistake
is corrected by a new entry, never by changing an old one.

## 4. Economy runs (H-18)

Economy sends the run to the provider's batch service at about half price and finishes within 24 hours; you keep
working and are notified. **Today only OpenAI offers it**: the others cannot find a batch again by a tag we give
it, so a lost reply could not be told from a batch that was never made. Turn it on under **Prices and Economy**
for a model (it needs a known price), choose **Economy** on a run, and the run waits (`Waiting to be sent`, `With
the provider`). **Cancel this run** works while it waits: a result that still arrives is kept and charged but
**never applied**. See [AI runs](./ai-runs.md) for every state. The browser journey does not cover Economy; the
backend tests do, with a real worker against a fake batch service.

## 5. The exit criteria

| Criterion | How you see it |
|---|---|
| Every run traced to its model and prompt version | Each run keeps the model that answered, every attempt, which prompt (version or one-off text) and a hash of what was sent |
| The budget stop works | Section 3 |
| No cross-coaching key use | Another coaching's Owner sees none of your keys, models, prompts or runs; a run uses only its own coaching's key (backend tests T43, T54 and the isolation test) |

## What is still yours to do

- Make and back up the **master key**, then enter your **provider keys** in the app.
- Run **`qbank ai-smoke`** once per provider you use (the adapters are unverified against the live services).
- Enter the **rupee rate** and a **budget** before real use, and set spend limits in each provider's own console
  as a second safety net.
- Read the four **platform prompt drafts** (migration 0038) and adjust them in the library.
- **Accept ADR-0009 and ADR-0023** (both still "Proposed") and read the choices in design note §15.
- Try one small **Economy** run with OpenAI before relying on it.
