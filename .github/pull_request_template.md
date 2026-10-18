## What & why
<!-- One or two sentences. Link requirement IDs (e.g. D-02, E-04) and ADRs. -->

## How it was tested
<!-- Exact commands run and their results. Screenshots for UI changes. Say what was NOT tested. -->

## Risks / rollback
<!-- Migration impact, feature flags, how to undo. -->

## Checklist
- [ ] Requirement IDs referenced; acceptance criteria met
- [ ] Tests added and run; CI green
- [ ] Permissions + tenant isolation covered for new endpoints/tables
- [ ] Audit events for significant state changes
- [ ] Migration reversible (or compensating action documented)
- [ ] Logs/metrics for new critical paths
- [ ] OpenAPI + generated client updated (if API changed)
- [ ] Docs updated; no secrets committed
