# 7. Question Ingestion Pipeline

## Goal

Convert PDF/DOC/DOCX source documents into reviewable structured question candidates without contaminating the production Question Bank with unreviewed data.

## Pipeline

```text
Upload
 -> Batch
 -> File validation
 -> Document extraction
 -> Page/block reconstruction
 -> Question segmentation
 -> Asset extraction
 -> Equation extraction/normalization
 -> Question structure extraction
 -> Answer extraction
 -> AI metadata proposal
 -> Duplicate candidate search
 -> Ingestion QC
 -> Commit to Draft Question Bank
```

## Step 1: upload

Requirements:
- Allowed file types.
- Maximum file size configurable.
- Virus/malware scanning before downstream processing.
- SHA-256 hash.
- MIME verification, not extension-only.
- Original file retained.

## Step 2: batch creation

Batch fields:
- Batch name.
- Subject.
- Exam.
- Year/period if known.
- Source attribution.
- Default language.
- Optional solution/answer-key relationship.

The batch owns all processing status and counters.

## Step 3: extraction

Preserve block-level source coordinates when possible:
- Page.
- Bounding box.
- Block order.
- Text.
- Image.
- Table.
- Equation.

The extraction result should be reproducible from the original document.

## Step 4: question segmentation

Detect:
- Question number.
- Stem start/end.
- Options.
- Solution start/end.
- Answer key references.
- Passage boundaries.

Use deterministic heuristics first, AI as a fallback or reconciliation layer.

## Step 5: passage handling

Store passage separately and link dependent questions.
Avoid duplicating identical passage text across every question.

## Step 6: equations

Store:
- Raw extracted equation.
- Normalized LaTeX or equivalent.
- Extraction method/confidence.

## Step 7: diagrams

Create an asset record and preserve:
- Original image/crop.
- Page location.
- Bounding box if available.
- AI description.
- Optional OCR text.

## Step 8: structure extraction

Output normalized JSON conforming to a question-type schema.

Example:

```json
{
  "type": "SINGLE_OPTION_CORRECT",
  "stem": [{"type": "paragraph", "content": "..."}],
  "options": [
    {"key": "A", "blocks": [...]},
    {"key": "B", "blocks": [...]}
  ],
  "answer": {"type": "OPTION", "value": ["B"]},
  "solution": null,
  "assets": []
}
```

## Confidence

Confidence must be field-level:

```text
stem: 0.99
type: 0.97
options: 0.98
answer: 0.72
solution: 0.94
diagram: 0.91
```

## Reprocessing

A batch can be reprocessed using a new extraction or AI pipeline without re-uploading the source.

Every processing run should record:
- Pipeline version.
- Parser version.
- Model versions.
- Prompt versions.
- Timestamp.

## Failure handling

Each item should have an explicit error state:
- UNSUPPORTED_DOCUMENT
- PARSE_FAILED
- SEGMENTATION_FAILED
- ASSET_FAILED
- STRUCTURE_FAILED
- LOW_CONFIDENCE
- DUPLICATE_REVIEW_REQUIRED

Retry only transient failures automatically.

## Commit behavior

The ingestion reviewer chooses:
- Create New Master.
- Attach to Existing Master.
- Create Variant.
- Mark Duplicate.
- Reject source item.

The selected decision becomes an auditable ingestion decision.
