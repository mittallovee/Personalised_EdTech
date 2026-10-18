# Official Technical References

Checked by reading official documentation on **18 October 2026**. These sources support design boundaries, not installed compatibility, account access, model quality or tested app behavior. Do not hardcode a latest version/model solely from this list.

| Source | Verified documentation point | Design consequence |
| --- | --- | --- |
| [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | Structured responses have schema support; refusal/incomplete output needs handling | OpenAI adapter validates operation output and handles refusals/incompleteness; schema shape does not establish answer truth |
| [Google Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output) | JSON Schema support has a supported subset and complexity limits | Verify selected endpoint/model; translate only supported constraints and still run app validators |
| [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | Structured output and strict tool use have schema limitations | Capability-specific adapter; no blanket JSON compatibility assumption |
| [OpenRouter structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs) | Check model support and require compatible routing parameters | Router support is not proof every upstream endpoint supports a task; record route/upstream evidence when available |
| [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) | Superusers/BYPASSRLS bypass policies; table owners normally bypass unless forced | Runtime is non-owner/non-BYPASSRLS; tenant policies and scoped platform paths need actual tests |
| [Celery introduction](https://docs.celeryq.dev/en/stable/getting-started/introduction.html) | Native Microsoft Windows is not supported | Propose Linux containers/WSL2 workers for this Windows PC |
| [Celery task behavior](https://docs.celeryq.dev/en/stable/userguide/tasks.html) | Task retry/acknowledgment behavior requires deliberate configuration and idempotent tasks | Durable checkpoints/output mappings; do not promise exactly-once broker execution |
| [Docker Desktop Windows installation](https://docs.docker.com/desktop/setup/install/windows-install/) | Supported backends and OS/WSL/hardware prerequisites are documented | Verify this PC before choosing/installing the container path |
| [Next.js self-hosting](https://nextjs.org/docs/app/guides/self-hosting) | Self-hosting involves proxy, environment and caching behavior | Tenant-sensitive responses/caches must remain scoped; public environment variables must contain no keys |
| [FastAPI container deployment](https://fastapi.tiangolo.com/deployment/docker/) | Container-based deployment is an available documented path | Proposed API image/service boundary; no container built here |
| [SQLAlchemy version counters](https://docs.sqlalchemy.org/en/20/orm/versioning.html) | Version counters assist detection of conflicting row updates, with usage limitations | Explicit transaction/revision guards remain necessary for all mutation paths |

## Not verified by this research

Specific model identifiers/defaults/prices, OCR or handwriting quality in seven languages, equation-editor interchange, legacy DOC conversion fidelity, exact software dependency versions, PC prerequisites, Docker licensing applicability, real credentials, SMS delivery, throughput, token savings and backup/restore.

Google API product selection (for example developer API versus another Google deployment route) is an implementation proposal to verify, not a new user-approved platform account choice. Provider support in the product means implementing and validating adapters, not assuming every model performs every modality.

The OpenAI Docs skill was used for the OpenAI API documentation portion. Other provider and engineering facts use their own primary documentation. No provider calls, credential validation or package installation occurred.
