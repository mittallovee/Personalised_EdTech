# 25. Analytics and Future Student Layer

This document defines the future architecture without making student delivery a prerequisite for the faculty/QB MVP.

## Student app goal

Deliver tests and capture fine-grained attempt behavior to enable analytics and personalization.

## Attempt model

At minimum:

```text
student
 -> test_attempt
     -> question_attempt
         -> response
         -> time spent
         -> selected options
         -> correctness
         -> review actions
         -> hint/solution usage
```

## Useful telemetry

For each question attempt:
- time to first interaction.
- total time.
- answer changes.
- selected/wrong options.
- attempts.
- skipped/visited.
- confidence if collected.
- solution/video viewed.

## Concept analytics

Because questions have concept/sub-concept tags, attempts can be aggregated by:
- concept.
- sub-concept.
- difficulty.
- question type.
- exam pattern.

## Personalization

Future recommendation inputs:
- accuracy.
- speed.
- misconception patterns.
- concept mastery.
- difficulty progression.
- recent exposure.
- question novelty.

## Recommendation safeguards

Do not recommend only the easiest or hardest questions.

Use a mix of:
- reinforcement.
- remediation.
- progression.
- exam-style practice.

## Data architecture

Keep high-volume attempt events separate from the transactional Question Bank where scale requires it.

Potential evolution:

```text
Transactional DB
       |
       v
Event stream / warehouse
       |
       v
Analytics tables
       |
       v
Recommendation service
```

## Minute-level concept tagging

The content model should permit fine-grained concept tags so future analytics can identify exactly what a question tests, e.g. a primary topic plus multiple supporting concepts.

This should remain metadata, not identity.
