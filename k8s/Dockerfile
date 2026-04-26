# syntax=docker/dockerfile:1.4
# Optimized multi-stage Dockerfile for speed and smaller images
# Stage 1: dependencies (cache pip between builds)
FROM python:3.12-slim AS deps
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir uv -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    UV_HTTP_TIMEOUT=300 uv pip install --system --no-cache -r pyproject.toml -i https://pypi.tuna.tsinghua.edu.cn/simple

# Stage 2: build/apply code (reuse dependencies cache)
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
  gcc libc6-dev zlib1g-dev curl \
  && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY . .

# Stage 3: runtime
FROM python:3.12-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl libgl1 libglib2.0-0 poppler-utils \
  && rm -rf /var/lib/apt/lists/* && apt-get clean
RUN useradd -m -s /bin/bash app
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app
RUN chmod +x /app/scripts/docker-entrypoint.sh && chown -R app:app /app
USER app
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
