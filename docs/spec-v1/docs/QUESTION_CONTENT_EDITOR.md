# Question Content and Equation Editor

Consolidation note (18 October 2026): confirmed policy is retained below; concrete engineering defaults are in [technical proposals](TECHNICAL_DESIGN_PROPOSALS.md). Any remaining engine/library/quality choices are implementation evidence work, not additional required user questions.

Status: visual equation editing, LaTeX source input and MathML source input confirmed for the first release on 17 October 2026. Canonical storage, conversion/rendering libraries and detailed UX remain design work. No editor has been implemented.

## Confirmed equation input methods

- Visual equation editor with structured controls.
- LaTeX code input.
- MathML code input.

Faculty may use the supported method appropriate to the expression. This extends shared manual-entry/correction content handling; it does not create a different question identity for each representation. Existing organization/edit permissions, version locking and QC apply.

## Shared question content

Support mathematical content where applicable in stem, options, solution, passage, statements and matching-column items. Preserve surrounding multilingual Unicode text, units, diagrams and source references. Correct-answer structure still follows the question type: formula input does not bypass integer/numerical/option-key validation.

## Proposed representation contract

Represent equations as identifiable structured content blocks with input format/source and rendering metadata as needed. The proposed canonical representation is typed rich blocks with equation format/source retained (QUESTION_SCHEMA_EXAMPLES.md). Editor/renderer libraries and supported conversion paths still require implementation evaluation. Do not assume every LaTeX construct has a lossless MathML/visual conversion or silently replace original source when a conversion is unsupported.

Maintain a preview consistent with saved/rendered question content and preserve the source/provenance needed for correction. Edits or representation switches must not silently change mathematical meaning; expose unsupported syntax and conversion warnings. Published versions retain stable expression/source/assets for historical rendering.

Imported equations should join the same correction/validation workflow rather than become unreadable opaque strings. Preserve uncertain OCR expressions with source context until corrected.

## Parser and rendering boundaries

Treat supplied markup as content. Use constrained MathML/XML handling without external-entity or arbitrary resource resolution, and a reviewed LaTeX/math rendering path without arbitrary command execution. Validate allowed structures and render safely. Exact supported syntax/macros, renderer/editor library, clipboard behavior and accessibility targets need evaluation; no complete standards-conformance claim is made.

## Acceptance direction

Use representative fractions, roots, superscripts/subscripts, integrals, matrices, units and mixed-language expressions in all applicable question fields. Verify visual/LaTeX/MathML entry, source retention, preview/saved-render agreement, visible unsupported conversion and permission/version integrity. No editor/library checks have been run.
