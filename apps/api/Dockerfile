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

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# In production, migrations are applied by a separate init container or
# pre-deployment hook, not by the application process itself.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
