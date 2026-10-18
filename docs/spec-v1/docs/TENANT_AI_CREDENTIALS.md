# Coaching-Owned AI Credentials

Consolidated 18 October 2026. Initial providers: Google, Anthropic, OpenAI and OpenRouter. Add more later through supported adapters/catalogue updates. No keys have been requested, stored or tested.

## Confirmed policy

Each coaching supplies its own API keys. No cross-coaching or centrally shared-key fallback. Coaching admin controls enabled supported models/default, faculty chooses enabled compatible options, and platform admin has protected full configuration authority. Ordinary faculty AI-tool access grants no provider-secret administration.

A missing/invalid key is visible; non-AI work remains available and AI-dependent stages cannot pretend success. Provider charges belong to the configured coaching account. Copying educational data to another coaching does not copy credentials/users/grants.

## Proposed secret lifecycle

P-25: encrypted per-coaching secret/reference with separate master key outside repository/database backup content, write-only settings, masked status/version/validation time, audited rotation/revocation. Workers resolve current authorized versions; expired/revoked credential failures cannot silently substitute another coaching's key.

Keep plaintext out of client bundles, normal APIs, logs/audit diffs, model prompts, content and documentation ZIPs. Platform full administration does not require plaintext display. Validate credentials only through explicit real integration steps later; provider selection does not establish account access.

## Catalogue and fallback

Verified capabilities/prices/API products/model identifiers remain engineering work. OpenRouter routing does not imply every upstream model supports all modalities. Store selected/actual provider/model and safe attempt evidence. Bounded compatible fallback shows failure and respects coaching budget, cancellation and actor authority.

No arbitrary user-configured executable endpoint behavior is inferred from extensibility. [Official references](TECHNICAL_REFERENCES.md), [orchestration](AI_MODEL_ORCHESTRATION.md), [budgeting](AI_USAGE_AND_COST.md).
