# 13. Test Builder

## Goal

Allow faculty to assemble reliable tests from approved/published question content using rich filters, availability indicators, and duplication controls.

## Test hierarchy

```text
Test
  -> Test Version
       -> Sections
            -> Test Questions
```

## Question eligibility

Default eligible status:
- APPROVED or PUBLISHED according to organization policy.

Recommended production tests use PUBLISHED questions only.

## Filters

At minimum:
- Organization.
- Subject.
- Chapter.
- Topic.
- Concept.
- Sub-concept.
- Difficulty.
- Question type.
- Exam.
- PYQ year.
- PYQ date.
- Source.
- Language.
- Text solution available.
- Video solution available.
- Diagram available.
- AI verified.
- Variant policy.

## Count availability

Every filter change should show:

```text
Available questions: 1,248
```

Counts must obey the same tenant, status, language, and eligibility rules as selection.

## Variant policy

Support:

```text
ALLOW_ALL
ONE_PER_MASTER
ORIGINAL_ONLY
VARIANTS_ONLY
```

Future policies may include:
- Max N per Master.
- Avoid same concept family.
- Avoid same source.

## Manual selection

Users can search and add specific question IDs.

## Random selection

Support deterministic randomization with a saved seed or selection snapshot so the draft can be reproduced.

## Blueprint

Future-friendly structure:

```text
Section: Mechanics
  10 questions
  difficulty distribution
  question type distribution

Section: Electrodynamics
  10 questions
```

Blueprint rules should be validated before finalizing.

## Ordering

Support:
- Manual drag-and-drop.
- Automatic ordering.
- Random shuffle at test-version generation.

## Solutions

Test configuration may optionally include or omit:
- Text solution.
- Video solution.
- Answer key.

## Publication

Publishing a test creates an immutable Test Version.

After publication, changes create a new Test Version rather than mutating the published one.

## Snapshot vs reference

Recommended:
- Keep question version reference.
- Store a publication snapshot/hash for reproducibility.

This prevents a later content edit from changing an already published test unintentionally.
