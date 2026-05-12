# ---- Stage 1: Build ----
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml .

RUN uv sync --no-dev

# ---- Stage 2: Runtime ----
FROM python:3.12-slim

WORKDIR /app

# Only copy the built venv from the builder stage
COPY --from=builder /app/.venv /app/.venv

COPY . .

RUN mkdir -p src/vector_store/uploads src/vector_store/chroma_db logs

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000 8501

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]