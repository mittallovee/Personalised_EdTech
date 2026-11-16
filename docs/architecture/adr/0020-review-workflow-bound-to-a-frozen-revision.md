# ADR-0020: The review workflow acts on one frozen revision, and a published version never changes
- Status: Accepted (owner approved 2026-11-16) · Date: 2026-11-15

## Context
M4 adds submit, return, QC, approve and publish (E-01, E-04). The risk is a reviewer approving text that the
author has since changed, two reviewers acting at once, or a published question changing afterwards. Authors
also save automatically every few seconds (M3), so any rule of the form "an edit cancels the review" would be
triggered by a stray keystroke.

## Decision
- **The state lives on the version** (`question_versions.state`), next to the revisions it protects. The policy
  (who may do each step, return reasons, queue, decisions) lives in a separate `review` module that calls
  `questions.public`; `questions` never imports `review`, so there is no cycle.
- **Submit freezes the working revision** and records it as the version's *review revision*. QC, approval and
  publication all act on that one revision. Reviewers read it, never the working copy.
- **While in review the editor is read-only.** Editing needs an explicit **Withdraw** (back to DRAFT). The
  server refuses a save to any version that is not DRAFT or CHANGES_REQUESTED (`QUESTION_NOT_EDITABLE`). A new
  submit freezes a new revision; old decisions stay in the history, bound to their old revision, and are never
  consulted to authorise the new one.
- **Every step after submit needs the version's workflow ETag** (`"flow-N"`, up by one on every state change)
  in `If-Match`, and takes a row lock, so a second request on a stale state gets `412 REVISION_STALE`.
- **One pure state machine** (`questions/domain/workflow.py`) is the only definition of the allowed steps; a
  database trigger repeats the allowed state pairs, and refuses any change to a PUBLISHED version or to its
  revisions, even for the table owner. `review_decisions` and `published_versions` are append-only.
- **The publication checklist is the findings engine** run on the review revision and the *current* catalogue
  and limits; Pass QC, Approve and Publish need no `error` and no `incomplete` finding, and Publish checks again
  inside its transaction.
- **A correction is a new version** under the same master and code; the master points at its published
  version until the new one is published. A snapshot of the English label names is stored at publication.

## Consequences
+ A stale approval cannot exist: there is nothing to go stale, because the reviewed text cannot change.
+ A bug in the service cannot publish a question that skipped a step: the database says no.
+ Two layers (code and trigger) hold the same rule; both are tested from one table.
− An author who wants to fix a typo during review must withdraw first (one extra click, by design).
− A question corrected after publication has two versions to read in history; the diff view (E-08) shows them.

## Alternatives considered
- *Any edit silently returns the question to DRAFT (as the spec table reads):* same effect, but autosave makes it
  happen by accident. Rejected in favour of an explicit withdraw (owner decision 2 in the note).
- *Workflow tables in a separate module that owns the state:* would need `questions` to ask `review` whether a
  save is allowed and `review` to ask `questions` for content, a cycle the import rules forbid.
- *A new revision per state change:* multiplies rows for no gain; the decisions table already records who did
  what to which revision.
