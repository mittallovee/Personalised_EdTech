# 11. AI Prompts, Schemas, and Provenance

## Prompt versioning

Never edit a production prompt in place.

Use:

```text
Prompt
  -> v1
  -> v2
  -> v3
```

Every AI job stores the exact prompt version used.

## Structured outputs

Prefer JSON schema-constrained outputs.

Example tagging output:

```json
{
  "questionType": "SINGLE_OPTION_CORRECT",
  "subject": "Physics",
  "chapter": "Laws of Motion",
  "topic": "Friction",
  "conceptTags": ["limiting friction", "coefficient of friction"],
  "difficulty": 7,
  "bloomLevel": "APPLY",
  "confidence": {
    "questionType": 0.99,
    "chapter": 0.95,
    "difficulty": 0.81
  }
}
```

## AI provenance fields

For every content-changing AI operation store:

```text
ai_job_id
organization_id
user_id
action
provider
model
model_version
gateway
prompt_version
input reference(s)
input hash
output
output hash
validation status
token usage
estimated cost
execution duration
created_at
```

## Input privacy

Only send the minimum necessary content to an external provider.

Potentially sensitive organizational/student data must be excluded from generic question prompts.

## Output validation

Pipeline:

```text
Raw model output
 -> JSON parse
 -> JSON schema validation
 -> Domain validation
 -> Safety/policy validation
 -> Application normalization
```

An AI response is not trusted merely because the model returned JSON.

## Determinism

Where provider/model supports it, record:
- temperature.
- top_p.
- seed if applicable.
- tool settings.
- system configuration.

## AI-generated question policy

AI-generated questions must be marked with a creation source and remain reviewable.

Recommended:

```text
AI_GENERATED
AI_MODIFIED
AI_TRANSLATED
AI_VERIFIED
```

`AI_VERIFIED` means an explicit verification action occurred; it must not mean “the AI generated it”.

## Reproducibility

For replay, store enough information to reconstruct:
- Input.
- Prompt version.
- Model version.
- Key generation parameters.
- Tool/schema configuration.

Provider output may still vary over time; provenance is for traceability, not a guarantee of byte-for-byte regeneration.
