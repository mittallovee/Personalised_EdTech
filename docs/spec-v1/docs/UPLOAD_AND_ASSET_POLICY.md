# Upload and Asset Policy

Consolidated 18 October 2026. Confirmed categories: PDF, Word (DOC/DOCX) and images; mixed bulk submissions. Confirmed per-file limits: **50 MB/document, 10 MB/image**. These are accepted project limits, not an industry-standard claim.

## Proposed technical interpretation

Decimal byte sizes: 50,000,000 and 10,000,000 bytes. Initial configurable transport bound 20 files/500,000,000 bytes per submission; larger collections use multiple background submissions. This guard does not cap the total question bank.

Raster intake: JPEG/PNG/WebP/TIFF/BMP, plus HEIF/HEIC via a verified decoder/conversion path. Extensions/signatures/MIME must agree; corrupted/unsupported content yields per-file errors. Broad category support does not authorize arbitrary executable/archive uploads or imply every decoder is already present.

Preserve original bytes and conversion provenance. Legacy DOC needs a tested isolated converter; macro execution is not an extraction feature. PDF encryption/corruption and decompression/page/pixel/time/memory limits receive explicit safe errors; choose detailed parser ceilings from representative fixtures, not invented benchmark guarantees.

## Ownership and processing

Originals are private organization assets with checksum/uploader/type/size. Reference-based serving validates current access; no arbitrary disk paths/public bucket objects. Extracted essential figures and published dependencies have independent retention references.

Upload success is not parsing/QC/publication success. Reject one invalid file without losing valid accepted items or falsely marking the batch wholly processed. Processing jobs persist stage/per-file state and permit further app work/new uploads.

Images may be whole question sources or diagram attachments; preserve that role and genuine image source coordinates. Multipage images/scan mixtures need tested recognition/coverage, not fabricated PDF anchors.

## Retention and deletion

Keep originals until admin chooses deletion; faculty may view available own-coaching originals. Storage analytics and original deletion are admin-only; platform admin full authority applies.

Delete checks source-job/pattern/copy and required-asset dependencies, records tombstone/receipt and preserves saved questions, essential diagrams, published history and independent destination-copy resources. A missing original is honestly shown unavailable.

[Source lifecycle](SOURCE_STORAGE_AND_RETENTION.md), [jobs](BACKGROUND_JOBS_AND_CANCELLATION.md), [recognition](OCR_AND_HANDWRITING.md), [technical proposals](TECHNICAL_DESIGN_PROPOSALS.md). No file engine or size-limit enforcement has been implemented.
