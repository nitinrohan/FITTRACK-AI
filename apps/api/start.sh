#!/bin/sh
# Production entrypoint: run migrations, then start the app.
set -e
echo "==> Running database migrations..."
alembic upgrade head
echo "==> Starting FitTrack API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 4
