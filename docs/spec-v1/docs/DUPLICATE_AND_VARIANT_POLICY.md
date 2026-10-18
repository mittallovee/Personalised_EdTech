# Duplicate Checking and Relationship Classification

Consolidation note (18 October 2026): current policy is retained below. [Technical proposals](TECHNICAL_DESIGN_PROPOSALS.md), [schema](DATABASE_SCHEMA.md) and [API](API_CONTRACTS_DRAFT.md) now provide concrete implementation recommendations; remaining empirical/engine choices are milestone work, not further required interview questions.


Status: automatic check for new questions confirmed on 17 October 2026. Confirmed exact intake duplicates attach source to the existing question without a new code; algorithms/thresholds and handling of already-existing duplicate masters remain under review. No matching quality has been evaluated.

## Confirmed scope

- Check every new question automatically against the active coaching's existing question bank.
- This covers manual/file-based new question intake; generated new question candidates use the same downstream processing/QC rules.
- Never search/expose another coaching's private question bank merely because question codes are globally unique.
- AI/exact/semantic matches are candidate evidence. Human QC remains authoritative before canonical/merge/duplicate relationship decisions.
- Preserve every source/candidate and uncertainty; do not silently drop extracted work or automatically publish/merge based on a similarity score.

## Distinctions to preserve

- Same-file/retry idempotency prevents repeated processing from creating duplicate masters; it is not identical to semantic question matching.
- Exact/near-duplicate suggestions need content evidence rather than primary-concept similarity alone.
- An intentional practice variant gets a new question code/master and variant-of link, preserving the original primary concept.
- A translation gets a new question code/master and translation-of/source-version link; shared meaning alone is not a reason to collapse those identities.
- Correcting an existing question creates a version under its existing code.

## Proposed evidence and review

Use checksum/normalized-content checks where appropriate and semantic candidates where useful. Preserve mathematics, units, options, diagram dependencies and answer meaning; normalization must not erase meaningful differences. Show accessible candidate matches, source/provenance and relationship evidence so review can distinguish exact duplicate, variation, translation and unrelated content.

Thresholds/confidence and ranking require a representative labeled corpus. Do not claim precision/recall or model accuracy without evaluation. Suggested matches and reviewer disposition should be traceable to the candidate/revision and matching configuration.

## Open disposition policy

User-confirmed: when intake is confirmed to be exactly an existing question, attach the new source to that master rather than creating another master/code. Preserve the matching version reference where applicable and keep provenance append-only; do not overwrite answer/content/metadata of a published version. Handling already-published duplicate masters, canonical links, historical code references and overrides needs explicit policy; no destructive merge/delete is implied.

## Acceptance direction

New intake automatically receives tenant-scoped checks with observable results. Fixtures distinguish exact duplicates, similar concepts with different answers, intentional variants, translations, diagram/math changes and replayed source files. Human disposition preserves original provenance and cannot leak cross-tenant matches. Tests have not been run.

## Large-bank candidate retrieval

Expected corpus size is in lakhs. Plan bounded same-coaching candidate retrieval before expensive matching; preserve human-confirmed duplicate disposition, sources and version evidence. Do not silently disable duplicate checking or introduce cross-coaching matching because the bank is large. Algorithms/indexes/thresholds and representative accuracy/performance measurements remain design work. See [capacity and performance](CAPACITY_AND_PERFORMANCE.md).
