# M5 demo: check AI assist and the prompt library yourself

M5 ("AI assist & prompt library") is done when the [phase plan](../product/02-phase-plan.md) exit criteria
hold: **every run is traced to its model and prompt version, a budget stops a run, and no coaching can use
another's key.** This page shows how to see each of those on your PC, then walks through everything M5 can do
in about an hour. Setup is in the [README](../../README.md#run-it-locally-windows-pc-with-docker-desktop); the
design is in the [M5 design note](../architecture/m5-design-note.md) and
[ADR-0009](../architecture/adr/0009-ai-platform.md).

Use made-up questions and `@example.com` emails. Never type real coaching content while testing, and never put a
real provider key into a screen you are recording or sharing.

## 0. Choose how to try it

**A. Without a provider key (recommended first).** The app has a built-in *demo provider* that answers every AI
call by itself: no network, no key, no cost. Its answers are plainly fake but always valid for the question
asked (a translation is the same text with the language name added; a verification adds "(checked)" to the
first line). Put this in your `.env` (copy `.env.example` first if you have not):

```
AI_KEYS_MASTER_KEY=<32 random bytes as base64, see .env.example for the one-line command>
AI_DEMO_PROVIDER=true
```

then `docker compose up --build -d`. The app refuses to start with `AI_DEMO_PROVIDER=true` when `APP_ENV` is
`staging` or `production`, so a hosted system can never serve made-up answers. In this mode you may type **any**
text as the key (for example `demo-key-1234567890`); it is never sent anywhere.

**B. With a real provider.** Leave `AI_DEMO_PROVIDER` off, set the master key, and follow
[ai-keys.md](./ai-keys.md): store your own key under Admin, AI, and run `qbank ai-smoke` once (add `--batch` for
Economy). A real run costs a small amount of real money.

Sign in as the Owner of a test coaching ([M2 demo](./m2-demo.md), steps 1 and 2) and make the syllabus you need
for tagging ([M3 demo](./m3-demo.md): a class, a subject, a chapter, a topic and one concept). Invite two
faculty, **Anita** and **Ben**, and open each activation link in a separate browser or private window.

## 1. Admin, AI: key, models, what each operation uses (H-02, H-03, H-05, H-17)

Menu → **AI** (Owner and admins only).

| Step | Expected |
|---|---|
| Under **OpenAI**, type any key and press **Save key** | "Stored, ending …" with the last four characters. The key is **write-only**: reload the page, view the page source, look at the network tab; it is never shown again |
| Under **Models**, press **Refresh the list** beside OpenAI | After a few seconds the models appear (with the demo provider: *Demo small* and *Demo large*, with prices). New models start **off** |
| Tick **Offer Demo small** | The box turns on once the server has saved it. The list under **What each operation uses** now offers it (without reloading the page) |
| **Prices and Economy** on Demo small: tick *This model offers Economy (batch) runs*, discount `0.5`, **Save** | "Economy runs are on (discount 0.5)." Economy is only ever offered for a model an admin has marked, with a known price, from a provider that can find a batch again (OpenAI and Google today) |
| Under **What each operation uses**, choose *Demo small* as the first model for all four operations, **Save** each | "Saved." Each operation now has a model to start from |
| Under **Rate and monthly budget**, enter `100` rupees per dollar and a default budget of `1000`, **Save** | "Saved. New runs use these numbers." Without a rate, budgets are off |

## 2. AI on a question as Anita (H-07 to H-10)

Anita starts a question (see [M3](./m3-demo.md)), opens it and chooses the **AI** tab. Each action opens a form:
**Prompt** (coaching default, one of *her* saved prompts, or a one-off for this run), **Extra instructions**,
**Model**, **How fast** (only if the model offers Economy), **Test run**, and what is left of her budget.

| Step | Expected |
|---|---|
| **Tag** → **Run tagging** | "Applied: difficulty 6, Bloom level APPLY". The chapter, topic and concept are filled in the **Edit** tab, where she can change any of them |
| **Solve** → **Run solve** | Two boxes, *Now* and *Suggested*, with the answer in words and a worked solution. **Nothing is written yet** |
| Press **Apply the answer and solution** | "Applied to the question." The **Edit** tab shows the new answer and solution |
| **Verify** → **Run verification** | Findings (with the demo provider, one made-up note) and, when the model is sure, *Now* and *Corrected* side by side. Nothing written yet |
| Press **Apply the correction** | "Applied to the question." The text in the **Edit** tab changes (the demo adds "(checked)") |
| **Translate**, choose Hindi, **Run translation**, then **Create the translation as a new question** | A link to a **new draft question** of her own, linked to the source. The original is not changed. Open the link: the text carries "[Hindi]" |
| Tick **Test run** and run Verify | The same call and cost, but there is no Apply button: a test never writes. It is the only way to run Solve or Verify on a question under review |
| Look at **AI history** (same tab) | Every run: what, when, its state, whether it was applied. Click one to read its result again |

**What is typed is safe.** Type a few words in the question, then go straight to the **AI** tab and run
something: the text is saved first and the run reads it; the editor is held still while a run is going, so
nothing typed can be replaced by an answer. If a run was made on an older text, applying it is refused ("the
question changed meanwhile") and nothing is written.

## 3. A budget stops a run (H-05, H-06; exit criterion)

| Step | Expected |
|---|---|
| As the Owner, give Ben a budget of 0 with `PUT /api/v1/ai/budgets/{his user id}` (body `{"monthly_inr": "0"}`, header `If-Match: "rev-0"`; there is no screen for a personal budget yet, only for the default) | Ben may not use AI |
| As Ben, start a question and run **Solve** | The form shows "This would pass your monthly AI budget." No provider is called, nothing is spent |
| Menu → **AI usage** as Ben | "Your budget for this month is used up." The Owner sees everyone's usage on the same page |
| Give Anita a small budget and use AI until she passes 80 % | One in-app notice "You have used 80% of your monthly AI budget"; at 100 % one more, and new runs are refused. The month is the calendar month in India time and starts again on the 1st |

## 4. Economy: half price, done later (H-18)

| Step | Expected |
|---|---|
| As Anita, **Verify**, tick *Economy (about half price…)*, **Run verification** | "This is an Economy run. You can keep working: you will be notified when it is done." The run is *Waiting to be sent* in **AI history**, and can be cancelled |
| Wait (about a minute with the demo provider; minutes to hours with a real one) | **AI history** shows *Done* by itself. The bell shows an unread notice "Your Economy verification has finished" that opens the question |
| Cancel a waiting Economy run | The run ends as cancelled and its reserved cost is given back. A result that still arrives after a cancel is kept and charged but **never applied** |

The worker process must be running (`docker compose` starts it). With the demo provider only an Economy
**verification** completes; the other operations need the question text, which the demo's stateless batch does
not keep, so they end as "did not finish". A real provider has no such limit.

## 5. The Prompt Library (H-13, H-14)

Menu → **Prompt library**. The full walkthrough is [ai-prompts.md](./ai-prompts.md); in short: read the prompt
each operation uses, make a **personal** prompt, test a draft against a real question (it counts in your budget
and never writes), and, with the *Manage AI prompts* grant, activate or roll back the coaching's prompt. Under
**Translation glossary** add a term (velocity → वेग): it is given to the translation prompt for that language.

## 6. The exit criteria

| Criterion | How to see it | Tests that prove it |
|---|---|---|
| Every run is traced to its model and prompt version | **AI history**: each run states the model that answered and the prompt kind used; the API run record names the exact prompt version, its hash and each attempt (and fallback) | `test_ai_orchestrator.py` (runs, attempts, one-off prompt kept on the run only), `test_ai_prompts.py` |
| A budget stops a run | Section 3 | `test_ai_budget.py` (refusal with what is left, 80 % and 100 % notices once, zero budget, two simultaneous runs cannot both pass), `test_ai_orchestrator.py` (refused before the provider is called) |
| No cross-coaching key use | Another coaching never sees your key, models, spend or runs | `test_ai_keys.py`, `test_ai_models.py`, `test_ai_budget.py`, `test_ai_orchestrator.py`, `test_every_tenant_table_is_isolated.py` |
| Economy is safe | A run is sent at most once; every ending settles its reservation; a result after cancel is never applied | `test_ai_economy.py`, `test_ai_batch_providers.py` |
| The AI screens work end to end | This page | `apps/e2e/tests/ai.spec.ts` (T55), `test_ai_demo_provider.py` |

## 7. What is still unproven

The real provider adapters are written from each provider's published documents and checked with recorded
answers; **none has been tried against the live service** until you run `qbank ai-smoke` (and `--batch` for
Economy) with your own key. Anthropic and OpenRouter have no Economy adapter yet. The cost of one run is not
shown before it starts; the form shows the model's price and your budget left, and the server refuses a run that
would pass the budget.
