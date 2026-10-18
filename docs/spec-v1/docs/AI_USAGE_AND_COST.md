# AI Usage, Cost and Monthly Budgets

Consolidated 18 October 2026. Confirmed: admin faculty-wise reporting, configurable monthly faculty limits, warning at 80%, stop new AI at 100%, reset on first day of each calendar month and retain prior history. No numerical default spending amount is approved.

## Reporting

For each logical run and billable attempt record coaching/requester, operation, selected/actual provider/model, status/time, available token/image/other usage, currency and cost evidence. Distinguish provider-reported actual, calculated estimate using a price version, and unavailable. Unknown is not zero; failed/retried requests are not assumed free.

Automatic ingestion/tagging/file-pairing work is attributed to the initiating faculty where valid. System work is labeled separately rather than inventing an actor. An operation with fallback is one product request but may have multiple billable attempts.

Admin management dashboard is scoped to own coaching; platform admin may inspect explicit targets. Faculty self-usage dashboard is not an added confirmed feature.

## Proposed enforcement

P-27/P-28: budget period uses configurable coaching timezone, default Asia/Kolkata. First-of-month selects a new period rather than erasing past ledgers. Dispatch reserves a bounded estimated maximum atomically against current usage plus concurrent reservations; fallback/retry reserves its cost too.

A run accepted into a queue is not authority to dispatch later past the limit. Recheck cancellation, current grants, credential, compatible model and budget at every provider call. If cost cannot be bounded from a verified catalogue, pause with a configuration issue rather than charge unknown work as zero.

Reconcile reported usage idempotently; distinguish estimates and late actual charges. Associate late billing with its original dispatch period, preserving current/historical views. An in-flight call may cost more than an estimate; display overrun honestly, do not promise the provider bill can never exceed a cap.

At 80% emit a deduplicated in-app threshold event; at 100% block new dispatch/reservations. Proposed warnings shown to the affected requester and coaching admins, without introducing an admin-only dashboard for ordinary faculty. Existing completed content and non-AI work remain available. Admin policy changes are audited.

## Credential/fallback separation

Each coaching uses its own provider keys. Failure fallback stays within enabled compatible options and the same budget; missing key/invalid cost basis does not authorize a shared-platform or other-coaching key. Preserve safe original/fallback failures and actual-provider evidence.

## Not subscription billing

Coaching subscriptions/payments are later. Application cost accounting records app calls, not every charge made by the coaching outside the app. No provider price, currency conversion rate, rupee forecast, free allowance or unlimited credit is selected.

[Orchestration](AI_MODEL_ORCHESTRATION.md), [credentials](TENANT_AI_CREDENTIALS.md), [proposals](TECHNICAL_DESIGN_PROPOSALS.md). No accounting/provider/concurrency tests have run.
