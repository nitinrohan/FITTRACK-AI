#!/bin/sh
# Production entrypoint: wait for DB, run migrations, start the app.
set -e

DB_URL="${DATABASE_URL:-}"

if [ -z "$DB_URL" ]; then
  echo "ERROR: DATABASE_URL is not set" >&2
  exit 1
fi

echo "==> Waiting for database to be ready..."
RETRIES=30
until python -c "
import psycopg2, sys, os
try:
    psycopg2.connect(os.environ['DATABASE_URL'])
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
# 1 worker on Render free tier (512 MB RAM). Upgrade instance for more workers.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1
