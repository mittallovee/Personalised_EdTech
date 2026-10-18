# AI Diagram Assistance — First-Release Requirement

Consolidation note (18 October 2026): current policy is retained below. [Technical proposals](TECHNICAL_DESIGN_PROPOSALS.md), [schema](DATABASE_SCHEMA.md) and [API](API_CONTRACTS_DRAFT.md) now provide concrete implementation recommendations; remaining empirical/engine choices are milestone work, not further required interview questions.


Status: user confirmed inclusion on 17 October 2026. Faculty-requested invocation is confirmed; image/model tooling, output representation, editing controls remain under review; faculty tool access is enabled by default. No diagram-generation or editing capability has been implemented or evaluated.

## Confirmed scope

- First release includes AI assistance to generate question diagrams and modify existing question diagrams when needed.
- Invoke diagram generation/editing only when faculty requests it. Do not automatically regenerate diagrams for every uploaded/new question or overwrite extracted source figures.
- The feature supports question authoring/variant workflows; it does not replace source-asset preservation during ingestion.
- Keep tenant ownership, private storage, asset provenance, human QC, immutable published versions and admin-defined approval/publication permissions.
- An AI-created diagram is not automatically verified or evidence that the associated question/answer is correct.

## Asset and question relationship

Store generated/edited results as traceable asset candidates with source question/version, input asset where relevant, model/provider, prompt/instruction/version, output identity and actor/time. Preserve original/source bytes. If attached to a published question, editing the diagram must create a new asset/version and controlled question version rather than replacing the bytes already referenced by historical tests.

Validate content and rendering compatibility, text labels, dimensions and tenant-safe references. Review geometric/physical meaning, units, scales, orientation, force/vector directions, connections and consistency with stem/answer. Visual plausibility alone does not establish scientific accuracy.

## Design choices still open

- Interaction with protected cross-author edits and provider configuration; faculty request is the confirmed trigger and default faculty tool access needs no per-user enable flag.
- Input controls, edit instructions, preview/selection behavior and original-versus-output comparison.
- Representation: vector, code-native diagram, raster, or a combination appropriate to the question; do not assume one model/tool satisfies every diagram.
- Supported providers/models/capabilities, budgets, timeouts, file/dimension limits and quality evaluation.
- Automatic consistency checks, required review evidence and replacement of draft assets.

## Acceptance direction

An authorized operation produces a reviewable asset without overwriting originals or published references. Trace generation/edit input and provenance; verify same-tenant attachment, invalid output handling, model/resource failures and old-version rendering after correction. Use representative Physics/question diagrams for evaluation before claiming subject accuracy. These are planned checks only.
