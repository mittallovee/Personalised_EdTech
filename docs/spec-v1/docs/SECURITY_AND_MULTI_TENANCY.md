# Security and Multi-Tenancy

Consolidated 18 October 2026. Isolation/authority/history are required; implementation mechanisms below are proposed.

## Trusted context

Authenticate canonical user → verify current coaching membership/action or platform authority → establish server-owned transaction context → validate same-coaching references → perform atomic change and audit. Do not trust organization IDs, roles or platform flags from document text, AI output or browser bodies.

Use non-owner/non-superuser/non-BYPASSRLS runtime DB credentials, deny-by-default RLS and composite tenant foreign keys. Test reads, inserts, updates, workers, graph counts, code lookups, storage and search against two coachings. Platform admin has full app authority through explicit target-scoped paths, not blanket database ownership.

## Identity and mutable authority

Verified method linkage only, no contact-match merges. Opaque server sessions/CSRF/rate limits and protected credential hashes are proposed. Membership/admin/Owner changes must take effect across sessions and queued work. Ordinary-faculty removal cannot target current admins/Owner through stale requests. Ownership transfer atomically preserves one Owner.

No user-facing device-management screen is required; backend expiry/revocation still is. No notification emails are required; authentication mechanisms remain.

## Untrusted content and storage

Documents/model output cannot execute code, SQL, shell commands, LaTeX programs or pattern scripts. Isolate DOC conversion/OCR and bound decompression/memory/time. Sanitize rich content; constrain MathML/XML and URL access, disable unsafe external entities/resources and preserve original source separately.

Originals/assets are private, served through authenticated opaque references. Source deletion is admin-only and retains required question/pattern/destination-copy assets. Never accept arbitrary filesystem paths or public object ACLs.

External video links are metadata, not a license to server-fetch arbitrary URLs. If a future feature fetches URLs, apply network/SSRF controls deliberately.

## AI, costs and secrets

Provider keys are coaching-owned, encrypted/protected and omitted from faculty responses, logs/audit diffs, prompts, browser bundles and documentation ZIPs. Full platform administration uses protected credential operations; raw-key exposure is not a requirement.

Catalogue capabilities, enabled models, data handling, budgets and current actor rights gate dispatch. Use reservations and reconcile late/unknown billing honestly. Failover stays within coaching credentials and compatible enabled models. Input prompt instructions cannot alter roles, expand tenant retrieval or bypass policy.

Generated answers/taxonomy are validated and provenance-bound. Schema validity or a successful model response does not establish educational truth, human QC or a verified badge.

## Integrity and operations

Append-only revisions and revision-bound workflow evidence; published assets/passage/labels pinned. Optimistic concurrency and idempotent output mappings prevent stale overwrite/replay duplicates.

Copy is platform-only, independent destination ownership/new codes, no users/keys/grants or live job/spend replay. Source provenance must not become a cross-tenant runtime access path.

Append safe audit events with actor/platform context, target coaching, entity/revision/action/reason/correlation. Record operational errors without exposing secrets. Retention/access/incident/production recovery policies remain later deployment work, not achieved guarantees.

[Local backup proposal](LOCAL_DEVELOPMENT_PLAN.md), [acceptance plan](ACCEPTANCE_TEST_PLAN.md), [official PostgreSQL and other references](TECHNICAL_REFERENCES.md). No penetration, RLS, auth, provider or restore checks have run.
