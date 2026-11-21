# AI runs: how an operation runs on a question

Part of M5 (see `docs/architecture/m5-design-note.md` §6). Tagging, solving, verifying and translating
are built, in Now and Economy modes.

## Running tagging

`POST /api/v1/questions/{id}/ai/runs` with `{"operation": "TAG"}`. The request needs:

- the **subject** chosen on the question (the model is shown that subject's active chapters, topics and
  concepts and may answer only with those ids);
- a **model** for the operation (Admin, AI) and that provider's **key** stored;
- an **editable question** (a draft or one with changes requested) unless `"test": true`.

The answer is checked (ids exist, the topic is under the chapter, difficulty is 1 to 10, Bloom is a known
level); a good one fills those labels on the working revision **only if the question has not changed since the
run began**. Otherwise the run keeps `apply_status` `OUT_OF_DATE` (it changed) or `NEEDS_REVIEW` (the person can
no longer edit it) and nothing is written.

## Solving and verifying: suggestions you apply

`SOLVE` and `VERIFY` **never write to the question by themselves**. The run's `result.output` holds the
suggestion and `result.before` what it would replace, so the screen can show old and new.

- **Solve** suggests an answer (in the shape of the question type: an option, options, a whole number, an exact
  value or a range) and a worked solution. The model is not shown the labels, the current answer or the current
  solution. The answer goes through the same validator as a person's save.
- **Verify** returns findings (path, severity `error` / `warning` / `note`, message; shown as plain text) and,
  only when the model is sure, a corrected version of the whole question. A correction must be a finished
  question that passes the validator, keeps the same type and keeps the labels as they were.

`POST /api/v1/ai/runs/{id}/apply` applies the suggestion, after a person has seen it. It is written to the audit
log (`AI_RUN_APPLIED`). It applies only to the exact revision the run read: if the question changed since, the run
becomes `OUT_OF_DATE` and nothing is written. The person applying must still be able to edit the question, and
must be the one who asked (or an admin). A test run can never be applied.

## Translating

`{"operation": "TRANSLATE", "target_language": "hi"}` on any question the person can open (it need not be
editable: the source is never changed). The model gets the whole question without its labels, the two language
names, and the coaching's glossary entries whose source term appears in the question (see `ai-prompts.md`).

The answer must have **exactly the structure of the source**: the same keys, option ids, answer, equations
and pictures, the same number of blocks. Only the words (text, picture captions and descriptions) may differ.
The labels are carried over from the source, not taken from the model. It must also pass the question validator
without new errors. Anything else is stored as `FAILED` (`AI_OUTPUT_INVALID`).

It is a suggestion until a person applies it (`POST /api/v1/ai/runs/{id}/apply`). Applying creates a **new
draft question** of that person, with its own code, linked to its source (`question_links`: the source and
the *version* that was translated). It applies only if the source is still at the revision the run read.
The new question carries `translation_of` when read, with `source_updated: true` once the source has published
a version newer than the one translated (D-13): worked out on read, never stored. The translation then goes
through the normal review workflow like any question; no AI run is ever a workflow step.

## Economy runs (about half price, done later)

`"mode": "ECONOMY"` (or the operation's default mode, set under Admin, AI) hands the run to the provider's
batch service instead of answering at once. The request returns immediately with the run `QUEUED`; the person
keeps working and is notified (`AI_RUN_FINISHED`) when it ends.

**Offered only** for a model the admin has marked as offering batch (with its discount), whose price is known,
and whose provider adapter can find a batch again by a tag we give it (the run's id). Without that, a lost reply
could not be told apart from a batch that was never made. 

**Which providers.** Only **OpenAI** offers Economy today. Its batches carry metadata and its list of batches
shows it, so a batch is found again by the run's id. Google's and Anthropic's published documents show no way
to find a batch by a tag we give it (Anthropic's custom ids are visible only once a batch has ended; Google's
list items document no name field), and OpenRouter has no batch service, so Economy is **not offered** for them:
a lost reply could not be told from a batch that was never made, and a run could be paid for twice. This can be
revisited if their documents change. Where the documents were unclear, the OpenAI adapter follows the
Responses API for the request body inside a batch (the documents do not show structured output inside a batch
body); it is **unverified against the live service** until the owner runs `qbank ai-smoke` and tries one
Economy run with a small question and a small budget.

States: `QUEUED`, `SUBMITTING`, `SUBMITTED`, then `SUCCEEDED`, `FAILED`, `CANCELLED`, `EXPIRED` or
`SUBMISSION_UNKNOWN`. Three background jobs do the work (the worker process must be running):

- **claim**: one conditional database update moves `QUEUED` to `SUBMITTING`, so only one job can win a run;
- **submit**: the provider is asked to make the batch **only on the job's first attempt**. After any error or
  restart it never sends again: it looks the batch up by the run's id and adopts it. If it is still not there
  after the last attempt (about ten minutes) the run becomes `SUBMISSION_UNKNOWN`;
- **collect**: asks the provider every minute at first, then every five minutes, then hourly, and gives up
  after 48 hours (providers promise 24).

**Money.** The budget reserves the discounted estimate when the run is queued. A result replaces it with the
real cost at the discounted price. A failed, expired or cancelled batch gives it back. `SUBMISSION_UNKNOWN`
keeps the whole reservation held, so a batch that may be running is never undercounted, until an admin settles it
with `POST /api/v1/ai/runs/{id}/resolve` (what the provider's billing shows, or nothing); that is audited.

**Cancelling** (`POST /api/v1/ai/runs/{id}/cancel`): before it reaches the provider the run simply ends. After
that the intent is recorded first and the provider is asked to stop; **a result that still arrives is kept and
charged but never applied**.

**Applying.** When the result arrives, the requester is loaded again: if they have left the coaching the result
is kept as `NEEDS_REVIEW`; if the question changed meanwhile it is kept as `OUT_OF_DATE`; tagging otherwise
applies by itself and solve, verify and translate stay suggestions applied by a click, exactly as for Now runs.
The result is checked against a snapshot of the question taken when the run was queued.

## Reading a run

`status` is `SUCCEEDED` or `FAILED`; a failed run is still returned (201) because the run is the record.
`error_code` on a failed run: `AI_OUTPUT_INVALID` (the answer was not usable; the provider was still paid),
`AI_PROVIDER_<KIND>` (`AUTH`, `RATE_LIMITED`, `TIMEOUT`, `UNAVAILABLE`, `BAD_REQUEST`, `BAD_OUTPUT`,
`TOO_LARGE`: nothing was charged) or `AI_RUN_ABANDONED` (the server stopped mid-run; the reservation was given
back). Each call to a provider is a row under `attempts`: a timeout, rate limit or outage tries the next model
of the operation's fallback list (at most two), the coaching's own keys only.

## Cost

The estimated cost is reserved before the provider is called and is replaced by the real cost (from the
provider's token counts and the model's prices) when the run ends. A person over their monthly budget is
refused before anything is sent. A run that begins and never finishes is closed, and its reservation given
back, the next time the same person starts a run.

## Not verified against a real provider

The orchestrator is tested with a scripted fake provider. Until the owner has run `qbank ai-smoke` for a
provider (see `ai-keys.md`), the real adapters are unverified against the live service.
