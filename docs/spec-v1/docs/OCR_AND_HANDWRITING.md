# OCR and Handwritten Question Extraction

Consolidation note (18 October 2026): current policy is retained below. [Technical proposals](TECHNICAL_DESIGN_PROPOSALS.md), [schema](DATABASE_SCHEMA.md) and [API](API_CONTRACTS_DRAFT.md) now provide concrete implementation recommendations; remaining empirical/engine choices are milestone work, not further required interview questions.


Status: handwritten question photo/scan support confirmed for the first release on 17 October 2026. OCR engines/models, evaluation corpus and accuracy targets remain design work. No extraction capability has been implemented or benchmarked.

## Confirmed scope

- Retain text extraction from text PDFs and OCR fallback for scanned sources.
- Support photos/scans containing handwritten questions and handwritten solutions in the first release, not only printed text; preserve solution steps/equations/diagrams and question associations.
- Use the shared candidate pipeline, source preservation, correction and QC workflow.
- Preserve original files and actual page/image/source anchors; faculty can inspect their coaching's original sources.
- Low-confidence or unsupported portions remain visible for correction rather than being silently dropped or presented as verified.

## Proposed extraction behavior

Identify text/image regions and use appropriate extraction/OCR for printed, handwritten or mixed content. Preserve question boundaries, options, equations, units, diagrams, tables and passage links where recognizable. Keep uncertain fragments and structural warnings alongside candidate content. An unreadable expression is not permission to invent its value or silently change its mathematical meaning.

If image preprocessing is used, retain the original and trace processed-image artifacts/configuration separately. Source anchors must reflect the actual file/page/image; do not invent PDF page references for standalone images. Confidence scores require a defined interpretation and evaluation; they are not proof of correctness.

Extracting an existing handwritten figure is different from generating/editing a diagram. Preserve the source figure through ingestion; AI diagram creation/editing remains faculty-requested under its separate confirmed workflow.

## Language and model requirements

Initial question languages are English, Hindi, Gujarati, Bengali, Marathi, Telugu and Tamil, with admin-extensible catalogue. Evaluate printed/handwritten script handling, mathematical notation and mixed-language sources explicitly. A language catalogue entry does not establish that a decoder/OCR/model has been tested for it.

The proposed self-hostable OCR option in the original stack is a candidate to benchmark, not evidence that handwriting works. Choose OCR/vision engines and fallbacks after representative-file evaluation. Provider calls, if used for extraction, must use the coaching's credentials, enabled compatible models, provenance and budget controls; do not invent provider charges for a local-only stage.

## Review and release evidence

Collect permission-cleared examples with neat/rough handwriting, skew/lighting variation, equations, subscripts/superscripts, symbols, diagrams and mixed printed/handwritten pages. Keep reviewed expected content/source boundaries. Measure completeness and human correction effort, not only successful job completion. Numerical accuracy/latency targets remain uncommitted until corpus review.

Test that uncertain candidates remain reviewable, authorized users can correct them, retry does not erase corrections, and source/tenant history is preserved. No application tests have been run.

## Existing corpus availability

User reports existing PDF/Word/image question sources are available. Both selectable/text-based material and scanned PDFs/photos are confirmed present. Their proportions, per-file/page mixtures and actual handwriting prevalence are not yet known. Use representative existing files for later extraction/OCR evaluation; do not infer OCR accuracy or a primary source format from availability alone. All previously confirmed printed/handwritten support remains required.

## Handwriting and reusable layout patterns

Patterns can describe handwritten question/solution regions, numbering and alignment; every new image still requires recognition. Do not reuse prior answer values or treat a known layout as recognized handwriting. Measure recognition versus structure-analysis costs separately and preserve uncertainty/source anchors. Samples are deferred, not a reason to stop documentation. See [patterns](ADAPTIVE_EXTRACTION_PATTERNS.md).
