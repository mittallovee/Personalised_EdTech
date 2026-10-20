# Documentation

| Folder | What it is |
|---|---|
| [`product/`](./product/) | **Our baseline (source of truth)**: requirements, phase plan, AI prompt library spec. |
| [`spec-v1/`](./spec-v1/docs/README.md) | Input/reference: consolidated package of 18 Oct 2026 (52 docs, unchanged, with its archive zips). |
| [`spec-v0/`](./spec-v0/) | Input/reference: earlier documentation pack (36 docs, unchanged). |
| [`architecture/`](./architecture/) | API style guide, ADRs (decision records), milestone design notes. |
| [`engineering/`](./engineering/) | Engineering standards: layout, coding, security, tests, CI, Definition of Done. |
| [`review/`](./review/) | Reviews of spec-v0 and spec-v1, recommended approach, open questions and vocabulary guide. |

## Start here

1. [Requirements](./product/01-requirements.md): every feature with ID, phase and origin.
2. [Phase plan](./product/02-phase-plan.md): Phase 1 milestones, later phases, stack, open questions.
3. [AI prompt library](./product/03-ai-prompt-library.md): view/edit/test/version AI prompts.
4. [Phase 1 scope](./product/04-phase-1-scope.md): **what we build first**: screens, journeys, in/out of scope.
5. [Engineering standards](./engineering/standards.md) and [`AGENTS.md`](../AGENTS.md): how code is written and checked.
6. [API style guide](./architecture/api-style-guide.md) and [ADRs](./architecture/adr/README.md): API rules and technical decisions.
7. [M1 design note](./architecture/m1-design-note.md): approved; the foundation milestone (done).
   [M2 design note](./architecture/m2-design-note.md): identity and coaching admin, **draft for approval**.
8. [M1 demo](./operations/m1-demo.md): check the foundation yourself; [remote access](./operations/remote-access.md) on your own domain.

## Review reading order (history)

1. [How the platform works](./review/01-how-the-platform-works.md): plain-language end-to-end walkthrough.
2. [Gap analysis](./review/02-gap-analysis.md): inconsistencies, missing areas, open decisions.
3. [Recommended approach](./review/03-recommended-approach.md): doc structure, architecture direction, stack, guardrails, next steps.
4. [Open questions](./review/04-open-questions.md): **needs product-owner answers** before spec-v1.
5. [Industry vocabulary](./review/05-industry-vocabulary.md): terms and the questions professionals ask.
6. [Review of spec-v1](./review/06-review-of-spec-v1.md): **latest**. What's strong, gaps to close before coding, 5 remaining questions.

Reviews 01–04 were written against spec-v0; where spec-v1 answers or changes something, 06 takes precedence.
