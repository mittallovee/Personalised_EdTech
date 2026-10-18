# 27. State Machines and Workflows

## Question version state machine

```text
DRAFT
  | submit
  v
IN_REVIEW
  | reject              | approve
  v                     v
REJECTED             APPROVED
                        |
                        | publish
                        v
                    PUBLISHED
                        |
                        | revise
                        v
                    DRAFT (new version)
```

## Allowed transitions

| Current | Action | Next | Actor |
|---|---|---|---|
| DRAFT | Submit | IN_REVIEW | Creator |
| IN_REVIEW | Reject | REJECTED | Reviewer |
| IN_REVIEW | Approve | APPROVED | Reviewer/Validator |
| APPROVED | Publish | PUBLISHED | Approver/Publisher |
| PUBLISHED | Revise | New DRAFT version | Authorized editor |
| Any eligible | Archive | ARCHIVED | Authorized role |

All transitions must be server-side commands, not arbitrary status updates.

## Ingestion item state machine

```text
UPLOADED
  -> PROCESSING
      -> EXTRACTED
          -> NEEDS_REVIEW
              -> DECIDED
                  -> COMMITTED

Any transient state -> RETRY
Permanent failure -> FAILED
```

## AI job state machine

```text
QUEUED
  -> RUNNING
      -> VALIDATING
          -> SUCCEEDED
          -> VALIDATION_FAILED
      -> FAILED
      -> CANCELLED
```

Retry rules depend on error class.

## Test version state machine

```text
DRAFT
 -> READY
 -> PUBLISHED
 -> ARCHIVED
```

Published test versions are immutable.

## Review conflict workflow

```text
Review A -> PASS
Review B -> FAIL
     |
     v
CONFLICT
     |
     v
EXPERT_RESOLUTION
     |
     +--> REJECTED
     +--> APPROVED
```

## Command model

Prefer explicit domain commands:

```text
SubmitQuestionForReview
ApproveQuestionVersion
PublishQuestionVersion
CreateQuestionRevision
ResolveIngestionItem
PublishTestVersion
```

Avoid generic `PATCH status=...` for lifecycle transitions.
