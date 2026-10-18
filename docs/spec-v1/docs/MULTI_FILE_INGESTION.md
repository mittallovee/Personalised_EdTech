# Linked Papers, Answer Keys and Solutions

Consolidation note (18 October 2026): current policy is retained below. [Technical proposals](TECHNICAL_DESIGN_PROPOSALS.md), [schema](DATABASE_SCHEMA.md) and [API](API_CONTRACTS_DRAFT.md) now provide concrete implementation recommendations; remaining empirical/engine choices are milestone work, not further required interview questions.


Status: bulk upload and association of separate question-paper/answer-key/solution files confirmed on 17 October 2026. AI identifies and links related files, and faculty may correct those associations afterward. No extraction/matching implementation exists.

## Confirmed product scope

- A bulk submission may contain multiple supported PDF, Word and image files.
- A question paper may be in one file and its answer key or solutions in another.
- AI identifies related question-paper, answer-key and solution files and links them for joint processing.
- Faculty can inspect and correct file associations afterward; manual pairing is not a mandatory prerequisite to processing.
- Preserve each file's identity, checksum, original storage and actual source locations.
- Existing per-file limits, tenant boundaries, source access/retention, candidate staging and publication QC still apply.

## Proposed association model

Represent document groups and source roles explicitly enough to distinguish unrelated papers inside one batch. A file may contain questions, keys, solutions or mixed content; do not assume all files in the same upload belong to one paper. Stable internal references and group context matter more than filenames.

Associate extracted questions with relevant answer/solution evidence using source numbering, paper identity and available context. Number 1 appearing in two papers is not sufficient to join them. Keep paper/file/page/paragraph references for stem, answer key, solution and assets independently so review can trace each value.

An extracted candidate may therefore reference more than one source location/file. The database/API design must not limit provenance to one filename/page when the answer came from another document. Retain schema/parser/matching provenance where applicable.

## Review and reliability

Keep unmatched keys/questions, ambiguous numbering and conflicting answers visible. Do not silently discard them, fabricate an answer or mark an association verified merely because extraction succeeded. Human QC remains authoritative for question correctness.

Retries/reprocessing must preserve group associations and avoid duplicate candidate/master creation or silent loss of prior human corrections. Original deletion follows admin-only policy; parsed question/answer content and required version assets remain preserved while deleted-source availability is shown honestly.

## Open workflow detail

AI discovers/links the files and faculty can correct associations afterward. Exact file-role/correction UI, matching confidence rules, repeated numbering/layout cases, retry scope and group progress need design/evaluation. This feature does not authorize cross-organization file links or prove matching accuracy.

## Acceptance direction

Use representative separate paper/key/solution documents, multiple unrelated papers sharing numbering, missing/conflicting keys and a mixed-content file. Verify correct group/source references, visible unresolved matches, tenant-safe links, retries and preserved reviewed content. Tests have not been executed.

## Automatic association and later correction — confirmed

AI may create file-group/role associations directly; preserve the evidence/model/prompt/input references and make them editable by faculty in the staging/ingestion workflow. File pairing is not proof that every extracted answer is correctly matched. Distinguish group association from question-number/content alignment. When a pairing is corrected, re-evaluate affected candidate answers/solutions with visible provenance and preserve prior human decisions/history instead of silently overwriting them. The correct version/review path applies to any already published content. This correction control does not grant blanket edit permission on another faculty's protected question or another tenant's files.
