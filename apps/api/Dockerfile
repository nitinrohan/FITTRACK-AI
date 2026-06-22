# ── Build stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System dependencies needed for psycopg2-binary and cryptography.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies before copying source so Docker layer cache
# is reused when only source files change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Development stage ──────────────────────────────────────────────────────
FROM base AS development

# Source is mounted as a volume in docker-compose so hot-reload works.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production stage ───────────────────────────────────────────────────────
FROM base AS production

COPY . .

RUN chmod +x /app/start.sh

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# start.sh runs: alembic upgrade head && uvicorn (with $PORT from Render env).
CMD ["/app/start.sh"]
