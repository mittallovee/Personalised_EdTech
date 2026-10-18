# 12. Search and Duplicate Detection

## Search goals

A faculty member should find the right questions quickly without memorizing IDs.

## Search types

### Exact
- Master ID.
- Question ID.
- PYQ code.
- Source code.

### Full text
Search stem, options, solution, and selected source fields.

### Fuzzy
Use trigram similarity for misspellings and wording differences.

### Semantic
Use embeddings/LLM-assisted candidate ranking once the MVP search baseline is stable.

## Retrieval pipeline

```text
Query
 -> tenant filter
 -> exact match
 -> lexical search
 -> fuzzy candidate retrieval
 -> optional semantic rerank
 -> permission/status filter
 -> result ranking
```

## Duplicate classes

```text
EXACT_DUPLICATE
NEAR_DUPLICATE
SEMANTIC_DUPLICATE
VARIANT
RELATED
UNRELATED
```

## Candidate generation

Use inexpensive deterministic features first:
- normalized question text hash.
- token fingerprints.
- source identifiers.
- option fingerprints.

Then use embeddings/AI for the smaller candidate set.

## Duplicate scoring

Example conceptual score:

```text
score =
  0.35 * lexical_similarity +
  0.35 * semantic_similarity +
  0.15 * option_similarity +
  0.15 * structure_similarity
```

Weights must be calibrated using real reviewed data.

Do not treat the example weights as production truth without evaluation.

## Threshold behavior

Example policy:

```text
< 0.70     likely unrelated
0.70–0.89 candidate for review
0.90–0.97 strong duplicate/variant candidate
> 0.97      very strong exact/near duplicate candidate
```

Thresholds must be tuned on labeled question-bank samples.

## Variant logic

A variant is not automatically a duplicate.

Use explicit relationships when:
- conceptual structure is shared.
- parameters are intentionally changed.
- the question is designed to be a separate usable instance.

## Test-builder implications

The system must support “one question per Master” selection rules.

A test can exclude:
- Same Master.
- Same Variant family.
- Same source question.

## Embeddings

Embed a normalized representation, not raw metadata noise.

Potential representation:
- question stem.
- option text where useful.
- solution may be excluded for basic similarity and used in a secondary signal.

Embeddings must be tenant-aware at query time even if the vector index itself is shared.
