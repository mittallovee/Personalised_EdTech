# Question Types — First Release

Consolidated 18 October 2026. All nine product formats below are confirmed. Payload representation/count-limit defaults are engineering proposals in [schema examples](QUESTION_SCHEMA_EXAMPLES.md) and P-14–P-18.

| Format | Structure | Correct-answer rule |
| --- | --- | --- |
| SCQ | Exactly four question-specific options | Exactly one correct option |
| Multiple correct | Exactly four options | One or more correct; a single correct choice is valid |
| Integer | Integer key | Inclusive 0–999, no fractions |
| Single digit | Integer key | Inclusive 0–9 |
| Numerical | One exact key OR one accepted range | 0.00–999.00, exactly two decimal places; one inclusive ordered interval only |
| Matching/list | Variable left/right item counts; exactly four mapping-combination options | Exactly one combination correct; each left matches one or more right items; correct mapping cannot reuse a right item across lefts; unused right distractors allowed |
| Assertion–reason | Assertion and reason; exactly four response options whose wording may vary by question | Exactly one correct option; no mandatory universal response template |
| Multiple statement | Variable statement count; exactly four combination/correctness options | Exactly one correct option |
| Passage-based | Shared immutable context, mixed concrete child types permitted | Each child is a separate master/code with its own answer rules and pinned context |

Passage is a context/group, not a duplicate numeric/option answer schema. Proposed implementation permits the eight concrete answer types as children and does not nest passage groups. Shared passage edits cannot rewrite published child content.

## Numerical rules

Maximum is **999.00**, not 999.99. 0.00 and 999.00 are valid. Range endpoints are included, within domain and lower ≤ upper. Exact versus range is explicit; no invented tolerance, multiple separate ranges or automatic widening.

If source/AI key has more than two decimal places, preserve it and flag for authorized review. 12.345 must not silently become 12.35. Do not discard the candidate or apply the answer constraint to every number appearing in a stem/solution.

No separate numerical-answer unit field, optional or required. Preserve units in source/stem/equation/solution; no silent conversion/rescaling. Proposed API encoding uses exact decimal strings and rejects a unit attribute in the numerical answer union.

Integer 0/999 accepted; -1/1000/fraction rejected. Single digit 0/9 accepted; -1/10/fraction rejected. Test scoring and partial credit are later scope.

## Matching details

A→P,R and B→Q is valid; A→P and B→P cannot both be correct. No requirement to use every right-column item. Apply no-shared-right validation to the selected correct mapping, not deliberately incorrect distractors.

Item count, assertion option text and multiple-statement count vary by question. Stable IDs and configurable resource limits are proposed; do not force a fixed global item count.

## Shared content and publication

All formats support Unicode language, equations/figures/tables, original evidence, metadata, optional solution and optional external video link. Visual, LaTeX and MathML equation entry are required. Incomplete drafts are saveable.

Publication requires valid content/answer, class, subject, one chapter/topic, primary concept, difficulty 1–10, Bloom and conditional PYQ exam/year, plus normal authorized workflow. Solution/subtopic/PYQ date/shift/paper code/video link are optional. See [publication checklist](PUBLICATION_REQUIREMENTS.md).

All formats must be supported in manual entry and downstream validation; this does not prove extraction of every layout. Source uncertainty remains visible until resolved. No tenth format, scoring model or test-delivery workflow is added by this specification.
