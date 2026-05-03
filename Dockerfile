# syntax=docker/dockerfile:1.6
# ---------------------------------------------------------------------------
# Roastline Coffee — Telegram shop bot
#
# Multi-stage Dockerfile. Stage 1 builds wheels in a fat builder image, stage
# 2 copies just the compiled wheels into a slim runtime — keeps the final
# image around 90 MB.
# ---------------------------------------------------------------------------

FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

COPY requirements.txt ./
RUN pip wheel --wheel-dir=/wheels -r requirements.txt


# ---------------------------------------------------------------------------

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Run as a non-root user — defence-in-depth.
RUN groupadd --system --gid 1001 botuser \
 && useradd  --system --uid 1001 --gid botuser --create-home botuser

WORKDIR /app

# Install runtime deps from prebuilt wheels (offline-style).
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# Copy application code.
COPY --chown=botuser:botuser . ./

# SQLite DB lives in a volume so it survives container rebuilds.
VOLUME ["/data"]
ENV DB_FILENAME=/data/shop.db

USER botuser

# Cheap health probe — `/start` doesn't need the bot to be running, but
# importing the module and connecting to SQLite proves the runtime is sane.
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import importlib; importlib.import_module('bot')" || exit 1

CMD ["python", "bot.py"]
