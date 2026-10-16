# 16. Security and Multi-Tenancy

## Tenant isolation

Every organization-owned table includes `organization_id` directly or via a strictly constrained parent relationship.

Every query must enforce tenant scope.

Never trust a tenant/org identifier supplied by the browser.

## Defense in depth

Use:
1. Application authorization.
2. Database constraints.
3. Optional PostgreSQL Row Level Security where compatible with the deployment.
4. Object-storage prefixes/bucket policies.

## Authentication security

- Secure password hashing through established library.
- Secure cookies/session storage.
- CSRF protection where cookie-based mutation is used.
- OAuth state/nonce verification.
- Rate limiting on login/reset endpoints.
- Account lock or progressive delays for abuse.

## Secrets

Never put provider/API credentials in frontend code.

Use environment/secret management:
- AI gateway keys.
- OAuth secrets.
- Database credentials.
- Storage credentials.

## File security

- Validate MIME type.
- Scan uploads.
- Reject unexpected embedded executables/macros where required.
- Store outside executable web roots.
- Generate signed URLs for protected assets.

## Authorization

Every sensitive operation checks:

```text
authenticated
AND active membership
AND correct organization
AND permission
AND object-level rule
```

## Audit

Log:
- Authentication events.
- Permission changes.
- Question edits.
- Review decisions.
- Approval/publication.
- AI actions.
- Source uploads.
- Test publication.

## Privacy

Minimize personal data.

Question-bank content is organization data. Avoid sending unrelated user/student data to AI providers.

## Encryption

- TLS in transit.
- Encryption at rest through managed database/storage where possible.
- Encrypted backups.

## Data export/deletion

Tenant deletion must be explicit, authorized, and auditable.

Avoid hard deletion of records required for compliance/audit until retention requirements permit it.
