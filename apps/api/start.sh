#!/bin/sh
# Production entrypoint: wait for DB, run migrations, start the app.
set -e

DB_URL="${DATABASE_URL:-}"

if [ -z "$DB_URL" ]; then
  echo "ERROR: DATABASE_URL is not set" >&2
  exit 1
fi

# Extract host and port from DATABASE_URL for readiness check.
# Format: postgresql://user:pass@host:port/dbname
DB_HOST=$(echo "$DB_URL" | sed -E 's|.*@([^:/]+).*|\1|')
DB_PORT=$(echo "$DB_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')
DB_PORT="${DB_PORT:-5432}"

echo "==> Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
RETRIES=30
until python -c "
import psycopg2, sys
try:
    psycopg2.connect('${DB_URL}')
    sys.exit(0)
except Exception as e:
    print(f'  not ready: {e}')
    sys.exit(1)
" 2>&1; do
  RETRIES=$((RETRIES - 1))
  if [ "$RETRIES" -le 0 ]; then
    echo "ERROR: database did not become ready in time" >&2
    exit 1
  fi
  sleep 2
done

echo "==> Database is ready."
echo "==> Running database migrations..."
alembic upgrade head

echo "==> Starting FitTrack API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 4
