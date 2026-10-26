# syntax=docker/dockerfile:1
# Adapted from livekit-examples/agent-starter-python.
ARG PYTHON_VERSION=3.12
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS base

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV HF_HOME=/app/.cache/huggingface
ENV TORCH_HOME=/app/.cache/torch

FROM base AS build

RUN apt-get update && apt-get install -y gcc g++ python3-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN mkdir -p src
RUN uv sync --locked --no-dev

# Pre-download model files (turn detector fallback, VAD, noise cancellation)
# before copying source, so this layer is cached across code-only changes.
RUN uv run --module livekit.agents download-files

COPY . .

FROM base

ARG UID=10001
RUN adduser --disabled-password --gecos "" --home "/app" \
    --shell "/sbin/nologin" --uid "${UID}" appuser

COPY --from=build --chown=appuser:appuser /app /app
WORKDIR /app
USER appuser

CMD ["uv", "run", "--no-dev", "src/main.py", "start"]
