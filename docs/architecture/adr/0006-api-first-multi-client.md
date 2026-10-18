# ADR-0006: API-first REST, OpenAPI contract, pluggable auth for many clients
- Status: Proposed · Date: 2026-10-18
## Context
Owner requirement: one backend callable by many frontends (faculty web now; student app, live-exam app, partners later).
## Decision
- All business logic behind versioned REST `/api/v1`; the web app uses only this API.
- OpenAPI generated from FastAPI, **committed** at `api/openapi.json`, CI fails on unintended or breaking changes (oasdiff); TypeScript client generated from it.
- Authentication is resolved by pluggable authenticators into one **Principal**: cookie session (web, P1); OAuth2/OIDC bearer tokens with PKCE (mobile, P4); client credentials (partners, later). Business code never reads cookies/tokens.
- Conventions in `docs/architecture/api-style-guide.md` (errors, pagination, ETag, idempotency, versioning).
## Consequences
+ New clients need no backend redesign; contract changes are visible in review.
− Discipline: no "quick" Next.js server shortcuts to the database.
## Alternatives
GraphQL (more flexible queries, more complexity; can be added later as a facade). Next.js server actions talking to DB (rejected: locks logic into one client).
