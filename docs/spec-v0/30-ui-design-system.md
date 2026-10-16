# 30. UI Design System and Components

## Product feel

The UI should optimize for professional academic operations rather than social-app aesthetics.

Priorities:
- dense but readable information.
- keyboard efficiency.
- predictable forms.
- clear status indicators.
- minimal context switching.

## Core component categories

### Navigation
- App shell.
- Sidebar.
- Breadcrumbs.
- Organization switcher where applicable.

### Data
- Data grid.
- Column selector.
- Filter chips.
- Pagination/cursor loading.
- Bulk selection toolbar.

### Forms
- Structured question editor.
- Metadata fields.
- Taxonomy picker.
- Source picker.
- Answer editor.
- Equation block.
- Asset picker.

### Workflow
- Status badge.
- Review checklist.
- Decision dialog.
- Approval panel.
- Audit timeline.

### AI
- AI action launcher.
- Model selector.
- AI suggestion card.
- Confidence indicator.
- AI provenance drawer.

## Question editor principles

Use content blocks rather than arbitrary HTML.

Example blocks:

```text
Paragraph
Heading
Equation
Image
Table
List
Callout
```

## Status display

Do not rely on color alone.

Example:

```text
[DRAFT]
[IN REVIEW]
[APPROVED]
[PUBLISHED]
```

Include accessible text/labels.

## Responsive behavior

The three-panel ingestion workspace can collapse to a tabbed mobile/tablet layout, but desktop is the primary reviewer experience.

## Performance

- Virtualize long grids.
- Lazy-load PDF pages/assets.
- Debounce search.
- Avoid fetching full question content for list rows.
