# Identity and Access

Consolidated 18 October 2026. Confirmed access policy below; concrete session/link/recovery implementation is proposed in P-08–P-11.

## Confirmed identity and onboarding

- Google, email/password and mobile OTP are supported alternative methods and can link to one canonical app account.
- Linked methods preserve one membership, grants, creator history and budget attribution. Verified explicit linking, not matching contact strings, establishes identity.
- Each faculty account belongs to one coaching and has no organization switcher. The same human's separately provisioned accounts are not automatically merged.
- Platform admin creates coachings and their first Owner; no public coaching self-signup.
- Coaching admins invite/create ordinary faculty. Multiple admins are allowed, appointed/removed by Owner or platform administration.
- Mobile/laptop concurrent sessions are allowed. No logged-in-device list or remote per-device logout UI; normal logout/backend expiry/revocation still apply.
- All notification delivery is in-app. This does not remove email/password login or invent a mandatory notification email for mobile-only users.

## Authority model

Platform admin has full supported application access across coachings, through explicit target context and audit. No automatic tenant-membership creation is needed to exercise platform authority; no unrestricted database-owner bypass is used.

Owner appoints/removes admins and may transfer ownership to another active same-coaching admin. Former Owner remains regular admin. Owner chooses whether an outgoing admin becomes faculty or loses app access. Ordinary admins cannot demote/remove Owner or peers through faculty-management routes.

All coaching admins may invite/create/remove ordinary faculty and configure ordinary faculty action grants, enabled AI models, cost limits and protected coaching settings within their scope. Branding changes remain platform-only. Account removal revokes coaching access and preserves coaching-owned questions, sources, usage and actor attribution.

Faculty sees the complete own-coaching bank and available originals. Upload/manual/AI are default tools. QC, approve, publish and cross-author edit are separate grants. Creator may act on own content with corresponding formal grants. No custom role-builder UI is required by confirmed policy.

## Proposed method/session design

Use canonical users, verified auth-identity links, active coaching membership/action grants and separate platform-role records. Google OAuth/OIDC, email/password and SMS OTP enter the same server-session flow. Password hashes use Argon2id through a maintained reviewed library; OTP codes/tokens are hashed, expire, rate-limited and attempt-limited. Current provider/libraries must be verified before implementation.

Method linking requires current account reauthentication and proof of the new method. A method already linked to another canonical account cannot be silently merged. Password reset/recovery cannot bypass membership revocation, create admin authority or union grants. Record identity events without secrets.

Proposed opaque session cookies, server-side hashed token lookup, CSRF defense, secure HTTPS flags, configurable 12-hour idle/7-day absolute expiry. Local loopback HTTP development requires an explicit development-only cookie configuration; never carry that setting into hosted production. Current membership/role is checked on requests, protected worker writes and provider dispatch.

Admin-created activation is proposed as a one-use 24-hour link shown/copied in app. An unactivated invitation is not an authenticated user or permission to access data. No notification-email integration is introduced. Real OTP delivery/OAuth credentials and verification/recovery flows are release gates, not additional product interview questions.

## Owner and membership transactions

Ownership transfer validates actor=current Owner/platform, distinct active same-coaching admin target and expected organization revision. Lock the relevant organization/role rows, atomically make target Owner and former Owner admin, audit and invalidate cached authority. Replays/concurrent transfers cannot create zero/multiple active Owners.

Ordinary faculty removal and admin demotion/removal verify the target's current role, preventing stale routes from removing a promoted admin/Owner. Revoke current access across sessions without deleting historical actors. Work already completed remains; future protected job writes/provider calls recheck authority and stop visibly when it is lost.

## Development and verification

A synthetic local identity fixture may support isolated foundation tests after implementation is authorized, but cannot be presented as completed Google/OTP/authentication integration. No real users/links/sessions/credentials have been created.

[Permissions](PERMISSIONS_MATRIX.md), [platform access](PLATFORM_ADMIN_ACCESS.md), [API](API_CONTRACTS_DRAFT.md), [security](SECURITY_AND_MULTI_TENANCY.md).
