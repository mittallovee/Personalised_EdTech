# AI runs: how an operation runs on a question

Part of M5 (see `docs/architecture/m5-design-note.md` §6). Tagging is the first operation; solve, verify and
translate use the same path (PRs 5f and 5g).

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
