# ADR-0023: Encrypting coaching API keys, and reaching AI providers over plain HTTP
- Status: **Proposed** · Date: 2026-11-21 · Refines ADR-0009
## Context
Each coaching enters its own provider keys (H-02). A leaked key costs real money, and the database is backed up
off the machine (K-16), so a stolen backup must not contain usable keys. The four providers (Anthropic, OpenAI,
Google, OpenRouter) each have an official SDK, but we need only a few calls (list models, one structured request,
and the batch calls), and a vendor SDK adds a large dependency surface to a service that holds other people's keys.
## Decision
**Keys at rest.** AES-256-GCM through the `cryptography` library. A **master key** (32 random bytes, base64) comes
from the environment (`AI_KEYS_MASTER_KEY`, with an id `AI_KEYS_MASTER_KEY_ID`) or the cloud secret manager, never
from the database or the repository. Each stored key has its own random 96-bit nonce; the coaching id, provider and
key id are bound as associated data, so a ciphertext copied to another row does not decrypt. The row also keeps
`last4` for masking. The clear key exists only in memory during a call, is wrapped in `SecretStr`, and is added to
the log and trace redaction lists. The API is **write-only**: set, replace, delete and a masked read; no route
returns a key.
**Rotation.** A new master key id is added alongside the old; `qbank rotate-ai-keys` re-encrypts every row under
the new one; the old one is removed afterwards. Without a master key the app starts, and AI features answer
`AI_NOT_CONFIGURED`.
**Reaching providers.** Plain HTTPS through `httpx`, one small adapter per provider behind the `AIProvider`
interface of ADR-0009. Base URLs are **fixed per provider** (never taken from a client or from the database), so
a user cannot point the server at an internal address (SSRF). Responses are size-capped before parsing, timeouts
are set on every call, and keys are sent only in the headers the provider documents. A fake transport serves
every test, so CI never calls a provider.
## Consequences
+ A database backup alone is useless to an attacker; a leak of one coaching's key cannot decrypt another's.
+ Few dependencies; one retry and timeout policy; adapters testable without the network.
− We write and maintain request shapes ourselves; a provider API change needs an adapter fix. The `qbank ai-smoke`
  command and the contract tests are how that is noticed.
− The master key is now something the owner must keep safe and back up separately; losing it loses all stored keys
  (they can be entered again).
## Alternatives
Vendor SDKs (more convenience, larger surface). LiteLLM (see ADR-0009). Storing keys with database-side
`pgcrypto` (the key would pass through SQL and could land in query logs).
