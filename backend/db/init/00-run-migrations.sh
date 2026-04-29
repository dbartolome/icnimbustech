#!/usr/bin/env bash
set -euo pipefail

MIGRATIONS_DIR="/docker-seed/migrations"

if [ ! -d "$MIGRATIONS_DIR" ]; then
  echo "ERROR: no existe $MIGRATIONS_DIR"
  exit 1
fi

echo "Aplicando migraciones SQL desde $MIGRATIONS_DIR"

mapfile -t FILES < <(find "$MIGRATIONS_DIR" -maxdepth 1 -type f -name '*.sql' | LC_ALL=C sort)

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "ERROR: no se han encontrado migraciones SQL en $MIGRATIONS_DIR"
  exit 1
fi

DEFERRED_SEED=""
ORDERED_FILES=()

for file in "${FILES[@]}"; do
  if [ "$(basename "$file")" = "010_seed_mvp.sql" ]; then
    DEFERRED_SEED="$file"
    continue
  fi
  ORDERED_FILES+=("$file")
done

if [ -n "$DEFERRED_SEED" ]; then
  ORDERED_FILES+=("$DEFERRED_SEED")
fi

for file in "${ORDERED_FILES[@]}"; do
  echo "-> Ejecutando $(basename "$file")"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f "$file"
done

echo "Migraciones aplicadas correctamente."
