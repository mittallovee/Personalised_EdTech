# 3. Roles and Permissions

## Roles

### Platform Admin
Controls SaaS-level configuration, tenants, AI model registry, system settings, and operational capabilities.

### Organization Admin
Manages an organization's users, policies, taxonomy usage, and operational settings.

### Creator / Faculty
Creates and edits draft content and submits it for review.

### Reviewer / Validator
Checks content correctness, answers, metadata, diagrams, solutions, and duplicate/variant classification.

### Approver
Approves content for publication.

### Test Creator
Builds tests from eligible content; may be combined with Creator/Reviewer depending on organization structure.

## Permission model

Use RBAC with resource-level checks.

Example permissions:

```text
question:create
question:read
question:edit
question:submit_review
question:review
question:approve
question:publish
question:archive
question:view_audit
question:manage_metadata
question:manage_sources
question:manage_ai
batch:create
batch:process
batch:review
batch:commit
 test:create
test:edit
test:publish
user:manage
organization:manage
```

## Separation of duties

Default policy:
- Creator can submit.
- Reviewer validates.
- Approver approves.
- Publisher/publishing capability executes final release.

Organizations may configure stricter rules.

Recommended default:
- A user cannot approve content they created.
- A user cannot publish content they rejected or altered after approval without re-approval.

## Access model

Every request resolves:

```text
Authenticated user
 -> organization memberships
 -> role/permissions
 -> resource tenant
 -> object-level policy
```

Deny by default.

## Domain restrictions

Support organization-configurable email domain restrictions. A deployment may initially restrict Google/email authentication to an approved domain such as `pw.live`, but the domain must remain configuration data rather than application code.
