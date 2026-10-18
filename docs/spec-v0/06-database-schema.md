# 6. Database Schema

## Principles

- PostgreSQL.
- UUIDs internally where useful; opaque short IDs for human-facing Master/Variant identifiers.
- Foreign keys for integrity.
- `created_at`, `updated_at` on mutable entities.
- Soft deletion only where business/audit requirements justify it.
- Published records are immutable by application policy.

## Core tables

### organizations

```text
id PK
name
slug UNIQUE
status
settings JSONB
created_at
updated_at
```

### users

```text
id PK
email UNIQUE
name
status
created_at
updated_at
```

### organization_memberships

```text
id PK
organization_id FK
user_id FK
status
created_at
updated_at
UNIQUE(organization_id, user_id)
```

### roles / permissions

Use RBAC tables if permissions are expected to evolve:

```text
roles
permissions
role_permissions
membership_roles
```

## Taxonomy

```text
subjects
chapters
topics
concepts
subconcepts
question_taxonomy_assignments
```

Prefer tenant-scoped taxonomy mapping, while allowing platform/global taxonomy catalogs later.

## Question tables

### master_questions

```text
id PK
public_id UNIQUE
organization_id FK
status
created_by
created_at
updated_at
```

### question_variants

```text
id PK
public_id UNIQUE
master_question_id FK
source_variant_id FK NULL
variant_type
creation_source
created_by
created_at
```

### question_versions

```text
id PK
variant_id FK
version_number
language_code
status
question_type
content JSONB
answer JSONB
solution JSONB NULL
has_text_solution BOOL
has_video_solution BOOL
created_by FK
creation_source
ai_job_id FK NULL
supersedes_version_id FK NULL
created_at
published_at NULL
UNIQUE(variant_id, language_code, version_number)
```

### question_version_taxonomy

```text
question_version_id FK
subject_id FK
chapter_id FK
 topic_id FK
concept_id FK
subconcept_id FK NULL
```

Alternatively normalize each assignment type if many-to-many relationships are required.

### question_source_links

```text
id PK
question_version_id FK
source_document_id FK NULL
source_reference_id FK NULL
source_page
source_question_number
source_exam_date NULL
source_code NULL
notes
```

## Ingestion

```text
ingestion_batches
ingestion_files
ingestion_pages
ingestion_items
ingestion_assets
ingestion_extractions
ingestion_decisions
```

### ingestion_batches

```text
id PK
organization_id FK
name
status
created_by
created_at
started_at
completed_at
```

### ingestion_files

```text
id PK
batch_id FK
filename
mime_type
size_bytes
sha256
storage_key
page_count
status
created_at
```

### ingestion_items

```text
id PK
file_id FK
source_page_start
source_page_end
source_question_number
status
extraction_confidence
question_candidate JSONB
created_at
updated_at
```

### ingestion_decisions

```text
id PK
ingestion_item_id FK
decision_type
existing_master_id NULL
existing_variant_id NULL
reviewer_id
reason
created_at
```

## AI tables

### ai_providers

```text
id PK
name
status
metadata JSONB
```

### ai_gateways

```text
id PK
name
base_url/config reference
status
```

### ai_models

```text
id PK
provider_id FK
gateway_id FK
code
name
capabilities JSONB
status
```

### ai_model_versions

```text
id PK
model_id FK
version
provider_model_identifier
context_window
input_cost
output_cost
status
released_at
deprecated_at NULL
```

### ai_actions

```text
id PK
code UNIQUE
name
description
```

### ai_action_models

```text
action_id FK
model_id FK
is_default
allow_user_selection
priority
UNIQUE(action_id, model_id)
```

### ai_prompts

```text
id PK
action_id FK
name
status
```

### ai_prompt_versions

```text
id PK
prompt_id FK
version
system_prompt
user_template
output_schema JSONB
status
created_at
```

### ai_jobs

```text
id PK
organization_id FK
user_id FK
action_id FK
model_version_id FK
prompt_version_id FK
source_entity_type
source_entity_id
status
input JSONB
output JSONB
validation_result JSONB
input_tokens
output_tokens
estimated_cost
started_at
completed_at
error_code
error_message
```

## Tests

```text
tests
test_versions
test_sections
test_questions
```

### tests

```text
id PK
organization_id FK
name
description
status
created_by
created_at
```

### test_versions

```text
id PK
test_id FK
version_number
instructions JSONB
settings JSONB
status
created_at
published_at
```

### test_questions

```text
id PK
test_version_id FK
question_version_id FK
position
section_id NULL
marks
negative_marks
snapshot JSONB NULL
```

Whether a final published test stores a content snapshot should be a product decision; recommended: store references plus a publication-time immutable snapshot/hash for reproducibility.

## Assets

```text
assets
asset_links
```

See `17-storage-and-media.md`.

## Audit

```text
audit_events
```

```text
id PK
organization_id FK NULL
actor_user_id FK NULL
action
entity_type
entity_id
before JSONB NULL
after JSONB NULL
metadata JSONB
request_id
created_at
```

## Indexing priorities

- Tenant ID on all tenant-owned tables.
- `public_id` unique indexes.
- Workflow status indexes.
- `(organization_id, status)` composite indexes.
- Question source/exam/year indexes.
- Taxonomy foreign keys.
- Test version/question lookup indexes.
- Full-text and trigram indexes after baseline query profiling.
