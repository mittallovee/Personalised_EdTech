# ADR-0014: The web app reaches the API through a same-origin proxy
- Status: Proposed · Date: 2026-10-19 · Milestone M1 (PR 5b)
## Context
The browser must send the `qb_session` cookie to the API, and the API refuses changes from other
web addresses (Origin allow-list, style guide §7). Calling the API on another host would need CORS
with credentials and third-party-cookie handling, which browsers increasingly restrict.
## Decision
- The browser talks only to the web app's own origin. The Next.js server forwards `/api/v1/*` and
  `/health/*` to the API (`rewrites` in `apps/web/next.config.ts`, target `API_INTERNAL_URL`, fixed
  at build time). No business logic runs in the proxy (AGENTS.md: everything goes through `/api/v1`).
- The web app calls the API only through `@qbank/api-client`, generated from `api/openapi.json`;
  it adds the `X-CSRF-Token` header on changes.
- **Client address.** Behind the proxy every connection comes from the web server, and
  `X-Forwarded-For` is forgeable (Next.js passes a client-supplied value through). The API therefore
  ignores it (`uvicorn --no-proxy-headers`) and uses one header named by `CLIENT_IP_HEADER` that the
  deployment's edge sets and clients cannot forge (Cloudflare: `CF-Connecting-IP`; a cloud load
  balancer's equivalent at M7), believed only from `TRUSTED_PROXIES`. Without it, per-IP sign-in
  limits count all users behind the proxy together (per-email limits still apply).
- A tunnel or load balancer in front routes the whole site to the web app (or `/api` and `/health`
  straight to the API: same origin either way).
## Consequences
+ First-party cookies, no CORS, one address to configure in `ALLOWED_ORIGINS`.
+ Mobile apps and partners (P4+) call `/api/v1` directly with tokens; nothing here changes for them.
− One extra hop for API calls from the browser. − The API address is baked into the web image at build.
