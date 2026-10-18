# 10. AI Platform and Model Gateway

## Objective

Provide a single application-facing AI interface while allowing platform administrators to manage multiple models/providers and allowing users to select among permitted models.

## Components

```text
Application
   -> AI Orchestrator
       -> Policy Resolver
       -> Model Resolver
       -> Prompt Resolver
       -> LiteLLM / AI Gateway
       -> Provider / Local Model
```

## AI Orchestrator responsibilities

- Validate AI action.
- Resolve organization/user policy.
- Select default or requested model.
- Resolve prompt version.
- Build structured input.
- Call gateway.
- Validate output schema.
- Record provenance.
- Record usage/cost.
- Return normalized result.

## Provider abstraction

The business application should not contain provider-specific code wherever avoidable.

Use provider/model identifiers in the AI configuration layer.

## Model registry

### Provider

Examples:
- OpenAI.
- Google.
- Anthropic.
- DeepSeek.
- Qwen.
- Local/self-hosted provider.

### Model

Logical model family.

### Model version

Specific provider model identifier/revision.

Historical AI jobs must point to an immutable model version record.

## AI action registry

Required actions:

```text
GENERATE_QUESTION
MODIFY_QUESTION
TAG_QUESTION
TRANSLATE_QUESTION
GENERATE_SOLUTION
VERIFY_QUESTION
ANALYZE_DIAGRAM
GENERATE_DIAGRAM_PROMPT
DETECT_DUPLICATE
GENERATE_EXPLANATION
```

## Action-model policy

For every AI action configure:
- Default model.
- Allowed models.
- User-selectable models.
- Priority/fallback.
- Required capabilities.
- JSON schema.
- Maximum token budget.
- Cost limits.

## User model picker

The UI should show a curated list rather than raw provider configuration.

Example:

```text
Action: Modify Question

Default: Model A

Available:
- Model A
- Model B
- Model C
```

Do not expose API keys or provider credentials to the browser.

## Fallback policy

Fallbacks are action-specific.

Example:

```text
Primary model unavailable
 -> approved fallback model
 -> retry transient error
 -> mark job failed
```

Do not silently change models on a deterministic content result without recording the actual model used.

## Cost controls

Support:
- Monthly organization budgets.
- Per-user quotas.
- Per-action token limits.
- Cost reporting.
- Optional approval for expensive models.

## Local models

The architecture must permit local models through the same gateway interface.
Examples include self-hosted Qwen/Llama-family deployments.

Local model availability is a deployment concern, not an application-domain concern.

## Model retirement

Models can be:
- Active.
- Deprecated.
- Retired.

Deprecated/retired models remain queryable for historical provenance and replay analysis.
