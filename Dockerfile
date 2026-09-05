# ---- Builder stage ----
FROM python:3.14-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ---- Runtime stage ----
FROM python:3.14-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
COPY --from=builder /app/.venv ./.venv
COPY src ./src
COPY alembic.ini alembic/ ./
ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "src.api.app:app"]