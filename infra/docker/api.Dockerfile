# Backend image: FastAPI API (and, from M1 PR 4, the worker via a different command).
FROM python:3.14-slim AS build
COPY --from=astral/uv:0.11 /uv /bin/uv
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
CMD ["uvicorn", "qbank.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
