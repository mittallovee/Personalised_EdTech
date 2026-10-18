# Database Schema — Proposed Logical Design

Consolidated 18 October 2026. This is a logical schema and integrity contract, not executed SQL or a migration. User-approved policies remain separate from P-01–P-35 engineering proposals.

## Identity and administration

| Table | Principal fields | Integrity |
| --- | --- | --- |
| organizations | id, display_name, logo_asset_id, state, revision, timezone | Branding mutation platform-only; timezone proposed Asia/Kolkata |
| users | id, status, display_name, created_at | Canonical attribution survives membership removal |
| auth_identities | id, user_id, method, verified_subject, verified_at, status | Unique provider/verified subject; verified linking only |
| password_credentials / otp_challenges | user or challenge IDs, protected hashes, expiry/attempt counters | No plaintext credentials/codes |
| memberships | id, organization_id, user_id, role, status, revision | Single active coaching membership per faculty account |
| organization_ownership | organization_id, owner_membership_id, revision | Exactly one active Owner; atomic transfer to active same-coaching admin |
| action_grants | organization_id, membership_id, action, granted_by | Separate QC/approve/publish/cross-author-edit; no default tool-enable flags |
| platform_roles | user_id, role, status | Full platform authority explicit, not inferred from tenant role |
| sessions / activation_tokens | id, user_id, token_hash, expires_at, last_seen, revoked_at | Concurrent sessions; no device-manager UI required |

## Content, provenance and workflow

Every tenant-owned table carries organization_id. Use composite unique keys (organization_id,id) and composite foreign keys to tenant-owned parents, so cross-coaching links fail even when IDs are known.

| Table | Principal fields | Integrity |
| --- | --- | --- |
| candidates | id, origin, creator_id, source_group_id, current_revision_id, disposition, warnings | Save incomplete manual/import/AI work; no invented source anchor |
| candidate_revisions | id, candidate_id, parent_id, schema_version, content_json, metadata_json, hash | Append-only snapshots; source/AI evidence retained |
| question_masters | id, permanent_code, creator_id, current_published_version_id, archived_at, revision | Globally unique eight-character code; not reused on archive/removal |
| question_versions | id, master_id, version_number, predecessor_id, state, current_revision_id | Unique master/version number; one active working version proposed |
| question_revisions | id, version_id, revision_number, parent_revision_id, content_json, metadata_json, hash, author_id | Immutable; typed schema validation and pinned dependencies |
| workflow_decisions | id, version_id, revision_id, revision_hash, action, actor_id, findings, time | QC/approval/publication evidence targets exact revision |
| question_relations | id, kind, from_master_id, to_master_id, source_version_id, evidence | Same coaching; variant-of/translation-of/duplicate; no silent identity collapse |
| duplicate_reviews | candidate_revision_id, target_version_id, evidence, disposition, actor | Exact intake attaches source without new master/code |
| question_sources | master/version/candidate references, source_anchor_id, provenance | Source attachments append without mutating published content |
| passage_masters / passage_revisions | identity, immutable content revision, hash, creator | No public passage question code required |
| passage_members | passage_revision_id, child_master_id, ordinal | Each child independently coded; child revision pins exact passage revision |
| revision_assets | revision_id, asset_id, purpose | Same-coaching immutable assets; protect historical rendering |

The ninth product format, passage-based, is a context/group. A child retains one concrete answer type and an exact passage revision. No recursive passage-in-passage structure is proposed.

Rich content schema is detailed in [examples](QUESTION_SCHEMA_EXAMPLES.md): paragraphs/equations/images/tables, stable option/item IDs, type discriminator and structured answer. Numerical keys use decimal strings in content; an optional relational index uses exact decimal numeric, never float. There is no numerical answer-unit attribute. Retain overprecision evidence without admitting an invalid key to publication.

Metadata carries class/subject/chapter/topic, optional subtopic, primary/multiple secondary concepts, language, 1–10 difficulty, Bloom, PYQ fields and optional video URL/solution. Published snapshots include labels/meaning as rendered then, not just mutable catalogue pointers.

## Taxonomy and graph

| Table | Principal fields | Integrity |
| --- | --- | --- |
| taxonomy_nodes | id, kind, parent_id, subject_id, class_id, state, provenance | Class/subject/chapter/topic/subtopic identities; validated hierarchy |
| concepts | id, subject_id, home_node_id, state, created_by_type | AI provisional usable immediately; admin review status independent |
| localized_labels / aliases | entity_id, language, label, normalized_alias, revision | Stable identity across languages; normalization cannot erase mathematical distinctions |
| concept_edges | id, prerequisite_id, dependent_id, subject_id, state, evidence, revision | Same coaching/subject; cross-class allowed; DAG cycle check proposed |
| taxonomy_events | entity/revision, action, actor, reason | Approve/edit/merge/revoke history; no published retroactive mutation |
| language_catalogue | organization_id, language_tag, label, state, capability_status | Initial seven languages; admin extension does not prove OCR/model quality |
| revision_concepts | question_revision_id, concept_id, role | One primary; distinct secondary IDs, no artificial limit of two |

Primary question chapter/topic are singular; secondary concepts may cross those branches within subject. A prerequisite graph is not the taxonomy parent tree. Merge/revoke maps future selection to valid entities while retaining old snapshot evidence.

## Originals, jobs and patterns

| Table | Principal fields | Integrity |
| --- | --- | --- |
| assets | id, checksum, kind, media_type, byte_size, private_locator, availability | No public arbitrary path access; immutable bytes |
| asset_ownership / asset_references | organization_id, asset_id, owner/purpose/reference | Destination copies retain independent logical ownership; physical dedup optional |
| source_files | id, asset_id, uploader, original_name, checksum, deleted_at | Original-retention tombstone separate from necessary derived assets |
| source_anchors | file_id, page/region/paragraph/image location, raw_reference | Match real source kind; no fabricated PDF pages for standalone images |
| ingestion_groups / associations | files, detected roles, evidence, revision, corrected_by | AI direct association and faculty correction; ambiguity preserved |
| jobs / job_attempts | type, actor, tenant, state, stage, revision, error, cancellation | Durable source of truth, not broker-only state |
| stage_checkpoints / job_outputs | job_id, stage/input_hash, output_key, output_id | Unique mapping prevents retries duplicating candidates/masters |
| extraction_patterns / pattern_versions | family_id, version, signature, config_schema, state, evidence | Tenant-specific; validated configuration, not generated executable code |
| pattern_runs / coverage_items | pattern_version, mode, input_regions, outcomes, usage refs | Each detected region extracted/flagged/skipped-with-reason; no fake full coverage |

## AI, budgeting and app events

| Table | Principal fields | Integrity |
| --- | --- | --- |
| model_catalogue | route_provider, model_identifier, capabilities, status, verification_date, price_version | Platform-supported only; no universal capability inference |
| tenant_model_settings | organization_id, catalogue_id, enabled, default_order | Enabled compatible choices; no key exposure |
| provider_credentials | organization_id, provider, encrypted_secret/ref, version, state | Secrets encrypted with separate master key; audit excludes plaintext |
| ai_runs / ai_attempts | operation, requester, source_revision, selected/actual route/model, prompt/schema, result/status | Logical run separate from billable attempts; safe failure history |
| faculty_budget_policies | organization_id, user_id, currency, monthly_limit, revision | No invented amount; admin controlled |
| budget_periods / reservations | actor, month/timezone, reserved, settled, cost_status | Atomic check/reserve; reset by new period, history retained |
| usage_ledger | attempt_id, units, amount, currency, evidence, price_version, dispatch_period | Idempotent reconciliation; unknown is not zero |
| notifications / recipients | event_id, organization_id, entity_revision, recipient_id, read_at | In-app only; unique event+recipient, current role checks |
| audit_events / domain_outbox | organization, actor/platform context, action, entity/revision, reason, correlation | Append-only safe evidence; outbox dispatches queue/app events, not emails |
| idempotency_records | organization, actor, operation, key, request_hash, result_ref | Changed payload conflicts; long-lived output mappings survive retry |

## Independent dataset copy

copy_operations pin source/target/cutoff/actor/status. copy_manifest_items record source snapshots/checksums and component dependencies. copy_mappings uniquely bind operation+source kind/ID/version to destination identity/code. copy_component_results record validation/activation/errors.

Destination content/source/assets/passages/taxonomy/graph/patterns are independent. Imported actor and source IDs are inert provenance, not destination membership/FKs granting source access. Do not copy users/auth/sessions/grants/provider secrets or replay source usage into destination budgets. Copied published content retains imported publication evidence and validated dependencies.

Proposed conflict policy: distinct import namespace and new identities; do not overwrite nonempty-target work or silently merge conflicting taxonomy. A source cutoff plus pinned assets protects against concurrent changes/deletion. Retry resumes mapping; never overwrites a destination edit as a resync.

## Indexes, integrity and migration

Use global code uniqueness; (organization_id,archive/status,subject,chapter,topic,language,type,difficulty,updated_at,id) indexes selected from real query plans rather than one huge combinatorial index. Index concept assignments/edges, source checksums, job state/time, pattern signatures and idempotency mappings. Tenant-scoped bounded duplicate retrieval precedes expensive comparison.

Runtime DB role is least-privilege, non-owner and not BYPASSRLS; enforce RLS including INSERT/UPDATE checks and fail closed without trusted context. Platform source/destination operations select authorized explicit contexts. Database constraints, service type validation and authorization are complementary.

Alembic migrations are proposed, forward corrective migrations for real persisted data and explicit destructive reset only for disposable fixtures. Backup/restore and tenant/immutability/concurrency checks must run once code exists. No migration, index plan, query benchmark or database test has run.
