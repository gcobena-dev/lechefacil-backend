#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head
echo "Migrations complete."

echo "Starting application..."
exec uvicorn src.interfaces.http.main:app --host 0.0.0.0 --port "${PORT:-8000}"
