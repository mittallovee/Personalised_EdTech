# Capacity and Performance — Requirements Review

Consolidation note (18 October 2026): current policy is retained below. [Technical proposals](TECHNICAL_DESIGN_PROPOSALS.md), [schema](DATABASE_SCHEMA.md) and [API](API_CONTRACTS_DRAFT.md) now provide concrete implementation recommendations; remaining empirical/engine choices are milestone work, not further required interview questions.


Status: qualitative faculty usage and lakh-scale question-bank expectation confirmed on 18 October 2026. No application, load benchmark or measured capacity exists.

## Confirmed workload direction

- Launch with one coaching and a small faculty group; support multiple coachings as previously agreed.
- Plan for a question bank containing lakhs of questions (a hundred-thousands-scale corpus), despite few initial users.
- No exact question count, hard corpus/user cap, concurrency target, storage allocation or response-time/throughput guarantee is confirmed.
- User reports existing question source material in the supported PDF/Word/image categories. Both selectable/text sources and scanned PDFs/photos are confirmed present; actual files/counts, proportions, handwriting prevalence and quality have not been inventoried or extracted during this requirements review.
- Stored corpus size and the rate of importing/generating it are separate. Initial bulk-load versus gradual accumulation, representative file/page/asset volume and simultaneous jobs remain to be clarified.

## Proposed engineering consequences

Keep the agreed modular monolith plus background workers and tenant-safe storage/database boundaries. A large bank does not itself authorize a microservices rewrite or a particular new search/vector provider.

Design question lists/search/filter/count and concept-linked navigation with bounded result retrieval and appropriate tenant/type/taxonomy/status indexes. Avoid loading the whole question bank into the browser, worker memory or one API response. Graph browsing should load the needed concept/neighborhood and linked-question results rather than materialize all questions as graph nodes. Exact pagination/index/query structures require the final schema and representative measurements.

Duplicate detection must find plausible own-coaching candidates before expensive comparison, retain traceability and human disposition, and avoid treating every new question as requiring an unbounded all-pairs corpus comparison. Specific algorithms/indexes/thresholds and accuracy evaluation remain separate design work. Imported/generated candidates preserve idempotency and normal question identity/version rules.

Large imports and AI/OCR operations remain background jobs, with progress, bounded work/concurrency, recoverable partial output and the confirmed cancellation behavior. Faculty can keep using the app/upload again. Provider/OCR costs and throughput are separate from database navigation speed; do not promise a completion time from corpus count alone.

Original-source retention, diagrams, solutions, versions and audit can dominate bytes independently of question count. Measure their distribution before choosing storage/backup/hosting capacity; do not infer an MB-per-question average or a monthly cost forecast from this answer.

## Planned evidence

When an implementation exists, use a disposable representative lakh-scale corpus and a separate second-coaching fixture. Record actual question/version/asset counts, data distribution, query filters, runtime/database configuration, concurrency and measurements. Exercise list/filter/count, concept navigation, duplicate candidate retrieval and background-import responsiveness with tenant isolation and platform authority intact.

Separate query latency, job throughput, provider latency, error rates, resource consumption and correctness. Set numerical acceptance targets after the workload/environment are chosen; successful toy-data checks cannot establish lakh-scale capability. Synthetic fixtures must not be reported as extracted/verified production questions. No capacity/performance test has run.

## Repeated layouts and future media workload

Multiple layout families each contain many source files. Evaluate AI bootstrap separately from known-pattern reuse, fresh handwriting recognition and drift fallback, measuring quality/tokens/time; samples arrive later. Future live/recorded/AI teaching media have separate bandwidth/storage/latency/cost workloads, not inferable from question-bank sizing. See [patterns](ADAPTIVE_EXTRACTION_PATTERNS.md) and [future learning](FUTURE_LEARNING_AND_AI_TEACHING.md).
