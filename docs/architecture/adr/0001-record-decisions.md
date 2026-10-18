# ADR-0001: Record architecture decisions as ADRs
- Status: Proposed · Date: 2026-10-18
## Context
The project will be built over years by a small team plus AI agents. Without a written "why", decisions get re-argued or silently reversed.
## Decision
Every significant technical decision is recorded as a short ADR in `docs/architecture/adr/`, numbered, with alternatives considered. Product decisions stay in `docs/product/01-requirements.md`.
## Consequences
Slight writing overhead; new contributors (and AI agents) can learn the reasoning quickly. PRs that change an accepted decision must add a superseding ADR.
