#!/usr/bin/env bash
set -euo pipefail

RUN_DB_MIGRATIONS="${RUN_DB_MIGRATIONS:-true}"

if [ "$RUN_DB_MIGRATIONS" = "true" ]; then
  echo "Aplicando migraciones..."
  /app/db/migrate_prod.sh
fi

echo "Arrancando backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
