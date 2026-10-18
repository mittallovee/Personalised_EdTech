# Question Ingestion Pipeline

Consolidated 18 October 2026. Manual, imported and generated work converge on shared type validation, duplicate disposition and human QC.

## Source-to-bank flow

1. Validate category/signature/per-file limit; retain a private original/checksum and create a durable background job.
2. Detect file/page content: selectable text, scan/photo, handwriting, mixed sections, figures/equations/tables.
3. Detect/associate papers, answer keys and solutions with AI evidence. Faculty can correct associations; unresolved numbering/pairing remains visible.
4. Match same-coaching layout patterns at document/page/section scope.
5. Unknown layout: AI extraction/discovery saves validated reusable configuration. Known compatible layout: read fresh content using saved rules and recognition as needed.
6. Validate coverage and structure; uncertain/drifted sections use visible AI fallback or remain unresolved if provider/budget unavailable.
7. Save candidates with source anchors, raw evidence, typed content/answers/assets, warnings and provenance. Overprecision is flagged, never rounded.
8. AI fills metadata directly and may extend provisional taxonomy; automatic own-coaching duplicate check returns evidence.
9. Authorized faculty corrects work. Human-confirmed exact intake attaches source to existing master; otherwise materialize new identity/code, including intentional variants/translations.
10. Submit through revision-bound QC/approve/publish; upload/extraction/AI completion never publishes.

Manual input starts at staged candidate without fabricated page anchors. AI variants/translations retain their exact source-version relationships and their own QC.

## Coverage and partial outcomes

Each detected source region/question is extracted, explicitly flagged unresolved or intentionally excluded with a visible reason. A header/pattern match does not prove complete document coverage. Keep unmatched keys, missing solutions, conflicting answers, handwritten ambiguity and unsupported assets inspectable.

Recognition, structure analysis, fallback, metadata and other AI costs/timings are separate. Pattern reuse is not an answer cache or persistent model memory. New handwriting still requires recognition. No token/throughput/accuracy improvement has been measured.

## Jobs and corrections

Jobs remain durable while faculty uploads more or navigates elsewhere. Proposed checkpoints/idempotent output mappings prevent retries creating duplicate candidates/masters. Own-job cancellation stops future stages cooperatively and keeps extracted unpublished drafts and already reviewed/published work.

Re-pairing files or correcting extraction creates new candidate/revision evidence and rechecks affected answers, without overwriting human-reviewed or published content. A late worker/AI completion checks revision and current actor rights. Original deletion coordinates active jobs and independently retained assets.

## Required source coverage

PDF/DOC/DOCX/images, printed/selectable/scanned/photo and handwritten questions/solutions in the seven-language catalogue. Preserve original language, formulas, diagrams and actual source location. Category support does not establish every source layout's extraction quality; DOC conversion/OCR/vision/editor paths need representative evaluation.

Source samples are explicitly deferred. Continue design now; later compare learning versus held-out layouts A/B/C, layout drift, mixed pages, handwriting and separate keys/solutions. Report quality, coverage, correction effort, tokens/time and measured capacity honestly.

[Upload policy](UPLOAD_AND_ASSET_POLICY.md), [patterns](ADAPTIVE_EXTRACTION_PATTERNS.md), [jobs](BACKGROUND_JOBS_AND_CANCELLATION.md), [schema](DATABASE_SCHEMA.md), [lifecycle](QUESTION_LIFECYCLE_AND_QC.md).
