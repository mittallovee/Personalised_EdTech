# 33. Risk Register

| Risk | Impact | Probability | Mitigation |
|---|---|---|---|
| PDF extraction errors | High | High | Staging + side-by-side QC + confidence |
| Wrong AI answer | Very high | Medium | Human validation + deterministic/numerical checks |
| Duplicate explosion | High | High | Candidate detection before Master creation |
| Tenant data leak | Critical | Low/Medium | Defense-in-depth tenant checks + security tests |
| AI provider outage | Medium | Medium | Gateway + fallback + retry |
| AI cost growth | High | Medium | quotas, budgets, action-level limits |
| Published content mutation | Critical | Low | immutable versions + server-side transition commands |
| Search degradation at scale | Medium/High | Medium | benchmark, indexes, dedicated search only when needed |
| Diagram/equation loss | High | Medium | asset preservation + visual QC |
| Workflow complexity | Medium | Medium | explicit state machines + narrow commands |
| Premature microservices | Medium | Medium | modular monolith first |
| Copyright/source issues | High | Variable | source metadata + organizational/legal policy |
| Operational complexity | Medium | Medium | EC2 first, Kubernetes only when justified |

## Risk review cadence

Review risks at major releases and whenever architecture changes materially.
