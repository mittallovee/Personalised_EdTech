# 15. Frontend Application

## Technology

Next.js + React + TypeScript.

## Core navigation

```text
Dashboard
Question Bank
  - All Questions
  - Create Question
  - Ingestion
  - Review Queue
  - Duplicates
Taxonomy
Tests
AI
  - AI Jobs
  - Model Selection
Reports
Admin
```

Menu visibility is permission-aware but not a security boundary.

## Key screens

### Dashboard

Show:
- Ingestion batches.
- Review backlog.
- Questions by lifecycle status.
- Recent AI activity.
- Test activity.

### Question Bank

Data grid with:
- Master ID.
- Version.
- Type.
- Chapter/topic/concepts.
- Difficulty.
- Language.
- Source.
- Solution/video availability.
- AI verified.
- Status.

### Question editor

Structured block editor for:
- Paragraphs.
- Equations.
- Images.
- Tables.
- Options.
- Answers.
- Solution blocks.

### Ingestion review

Three-panel source/extracted/QC workspace.

### Content review

Focused review page with:
- Current version.
- Original/source context.
- Previous version comparison.
- Review checklist.
- Reviewer comments.
- Audit history.

### Test builder

Two-pane recommended layout:

```text
Filters / bank results | Test composition
```

Show live counts and eligibility.

## UX rules

- Preserve unsaved edits.
- Warn before destructive navigation.
- Save drafts frequently.
- Optimistic UI only for low-risk state changes.
- Explicit loading/error states.
- Keyboard-first review workflows.
- Virtualize large tables.
- Debounce search.

## Rich text/math

Store normalized content blocks. Render equations through a controlled math renderer.

Do not allow arbitrary HTML injection.

## Accessibility

- Keyboard navigation.
- Focus management.
- Semantic labels.
- Sufficient contrast.
- Screen-reader descriptions for diagrams where available.
