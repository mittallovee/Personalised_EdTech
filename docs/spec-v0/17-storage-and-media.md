# 17. Storage and Media

## Storage split

### PostgreSQL
Store:
- Metadata.
- Structured question content.
- Relationships.
- Workflow state.
- AI provenance.

### Object storage
Store:
- Original PDFs.
- DOC/DOCX files.
- Extracted images.
- Diagram assets.
- Video references/thumbnails.
- Generated exports.

## Storage key scheme

Example:

```text
org/{organizationId}/sources/{batchId}/{fileId}/original.pdf
org/{organizationId}/ingestion/{itemId}/assets/{assetId}.png
org/{organizationId}/questions/{masterId}/{versionId}/...
org/{organizationId}/exports/{exportId}/...
```

Do not expose raw storage keys to untrusted clients.

## Asset entity

Fields:

```text
asset_id
organization_id
storage_key
mime_type
size_bytes
sha256
width
height
created_at
metadata
```

## Asset links

Link an asset to:
- Ingestion item.
- Question version.
- Solution.
- Test/media package.

## Image processing

Generate appropriate derivatives:
- Original.
- Web-sized preview.
- Thumbnail.

Do not overwrite originals.

## Video solutions

The question bank stores video metadata/reference, not necessarily the video binary.

Fields:
- provider.
- external video ID/URL.
- duration.
- thumbnail.
- language.
- status.

## Retention

Original source files should be retained according to organization policy because they provide the authoritative ingestion evidence.
