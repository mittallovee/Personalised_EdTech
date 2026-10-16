# 5. Question Domain Model

## Core identity model

```text
Master Question
    |
    +-- Variant (0..N)
    |      |
    |      +-- Version (1..N)
    |
    +-- Original/default variant
           |
           +-- Version (1..N)
```

Language is a property of a content version/translation lineage, not a new Master identity.

## Master Question

Represents conceptual identity only.

Attributes:
- master_id
- organization_id
- canonical_subject_id (optional)
- lifecycle state
- created_at / updated_at

The Master itself does not store the student-facing question text as the authoritative content.

## Variant

Represents a question derived from the same conceptual/source family but with meaningful content changes.

Examples:
- Parameter-modified numerical.
- Different values.
- Different scenario using same underlying pattern.
- AI-generated intentional variation.

Attributes:
- variant_id
- master_id
- variant_type
- source_variant_id (optional)
- creation_source

## Question Version

Represents an immutable snapshot of a specific variant/language content state.

Attributes:
- version_id
- variant_id
- version_number
- language_id
- status
- content blocks
- answer
- solution
- metadata snapshot/references
- created_by
- creation_source
- ai_job_id
- created_at

## Question types

Canonical enum values:

```text
SINGLE_OPTION_CORRECT
MULTIPLE_OPTION_CORRECT
NUMERICAL
INTEGER
SINGLE_DIGIT
MATCH_THE_COLUMN
ASSERTION_REASON
MULTIPLE_STATEMENT
PASSAGE_BASED
PASSAGE_SCQ
PASSAGE_NUMERICAL
PASSAGE_MCQ
```

Do not assume every type has options.

## Content representation

Prefer structured blocks:

```json
{
  "blocks": [
    {"type": "paragraph", "content": "..."},
    {"type": "equation", "latex": "v = u + at"},
    {"type": "image", "assetId": "..."},
    {"type": "table", "rows": [...]}
  ]
}
```

This supports rich editing and deterministic rendering.

## Answer representation

Store normalized answer data separately from rendered answer text.

Examples:
- SCQ: option key.
- MCQ: array of option keys.
- Numerical: accepted numeric value/range/rules.
- Integer: integer value.
- Single digit: 0–9.
- Match: mapping pairs.
- Assertion/Reason: structured option selection.

## Solutions

A question may have:
- No solution.
- Text solution.
- Stepwise solution.
- Video solution.
- Multiple solution methods.

Track availability with explicit metadata so Test Builder filters are cheap and reliable.

## Source relationship

A question may have multiple sources.
A source does not define question identity.

Examples:
- JEE Advanced 2022.
- Coaching module.
- Faculty worksheet.
- Imported PDF.

## Taxonomy relationship

Taxonomy assignments are references, not identity.

A question may be retagged later without changing its Master ID.

Recommended hierarchy:

```text
Subject
  -> Chapter
     -> Topic
        -> Concept
           -> Sub-concept
```

The taxonomy must remain configurable and expandable beyond the initial exam structure.

## Permanent ID

Use generated opaque IDs. Do not encode subject/chapter/year into the permanent identifier.
