# Backend image: FastAPI API (and, from M1 PR 4, the worker via a different command).
# The uv tool image is its own named stage so that Dependabot (which reads FROM lines, not
# COPY --from) can propose updates for it.
FROM astral/uv:0.11 AS uv

FROM python:3.14-slim AS build
COPY --from=uv /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Install dependencies first (cached layer), then the project itself.
COPY services/api/pyproject.toml services/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY services/api/ ./
RUN uv sync --frozen --no-dev

FROM python:3.14-slim AS runtime
RUN useradd --create-home --uid 10001 app
COPY --from=build --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
USER app
EXPOSE 8000
# --no-proxy-headers: never rewrite the client address from X-Forwarded-For (anyone can send it);
# the trusted client-IP header is handled in core/clientip.py (ADR-0014).
CMD ["uvicorn", "qbank.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
