# ADR-0003: Python/FastAPI backend, Next.js/TypeScript web, monorepo
- Status: Proposed · Date: 2026-10-18
## Context
Hardest problems are document parsing, OCR/vision extraction and AI orchestration. The backend must serve many future clients through a typed contract. Development on a Windows PC, later cloud.
## Decision
- Backend: **Python** (latest stable at M1, ≥ 3.13), **FastAPI**, **Pydantic v2**, managed with **uv** (lockfile).
- Web: **Next.js + React + TypeScript** (strict), Tailwind + shadcn/ui, TanStack Query, managed with **pnpm**.
- Maths: **KaTeX** rendering, **MathLive** visual editor.
- Monorepo layout as in `docs/engineering/standards.md`.
- Local dev: Docker Desktop + WSL2 (`docker compose up`).
Exact versions are pinned during M1 after checking current stable releases.
## Consequences
+ Best libraries for PDFs/images/AI; FastAPI generates OpenAPI from typed models.
+ TypeScript client generated from OpenAPI keeps web and API in sync.
− Two languages (Python, TypeScript); mitigated by strict typing and generated client.
## Alternatives
TypeScript/NestJS backend (weaker document/AI ecosystem). Java/Spring (heavier for a small team).
