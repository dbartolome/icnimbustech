#!/usr/bin/env bash
set -euo pipefail

# Exporta datos MVP de una BD PostgreSQL ya poblada y actualiza:
# - backend/db/seeds/seed_mvp.sql
# - backend/db/migrations/010_seed_mvp.sql

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEED_FILE="$ROOT_DIR/backend/db/seeds/seed_mvp.sql"
MIGRATION_FILE="$ROOT_DIR/backend/db/migrations/010_seed_mvp.sql"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL no está definida."
  echo "Ejemplo:"
  echo "  DATABASE_URL='postgresql://sgs_user:sgs_pass@localhost:5433/sgs_dev' ./backend/db/export_seed_mvp.sh"
  exit 1
fi

mkdir -p "$(dirname "$SEED_FILE")"

PG_DUMP_ARGS=(
  --data-only
  --inserts
  --column-inserts
  --no-owner
  --no-privileges
  --table=public.alertas
  --table=public.audit_log
  --table=public.audit_role_changes
  --table=public.catalogo_servicios
  --table=public.conversaciones_ia
  --table=public.cross_selling_intelligence
  --table=public.cuentas
  --table=public.documentos
  --table=public.forecast_snapshots
  --table=public.importaciones
  --table=public.informes_generados
  --table=public.manager_sbus
  --table=public.matriz_sectorial
  --table=public.notas_voz
  --table=public.oportunidades
  --table=public.owner_cross_sell_queue
  --table=public.productos
  --table=public.sbu
  --table=public.sesiones_audio
  --table=public.usuarios
)

TMP_ERR="$(mktemp)"
cleanup() {
  rm -f "$TMP_ERR"
}
trap cleanup EXIT

if pg_dump "$DATABASE_URL" "${PG_DUMP_ARGS[@]}" >"$SEED_FILE" 2>"$TMP_ERR"; then
  :
else
  if grep -q "server version mismatch" "$TMP_ERR"; then
    if ! command -v docker >/dev/null 2>&1; then
      echo "ERROR: pg_dump local incompatible con PostgreSQL servidor y docker no disponible."
      cat "$TMP_ERR"
      exit 1
    fi

    echo "Aviso: pg_dump local incompatible. Reintentando con postgres:15 en Docker..."

    DOCKER_DATABASE_URL="$DATABASE_URL"
    DOCKER_DATABASE_URL="${DOCKER_DATABASE_URL/@localhost:/@host.docker.internal:}"
    DOCKER_DATABASE_URL="${DOCKER_DATABASE_URL/@127.0.0.1:/@host.docker.internal:}"

    if ! docker run --rm postgres:15 pg_dump "$DOCKER_DATABASE_URL" "${PG_DUMP_ARGS[@]}" >"$SEED_FILE"; then
      echo "ERROR: fallo al exportar seed usando pg_dump de postgres:15 en Docker."
      exit 1
    fi
  else
    cat "$TMP_ERR"
    exit 1
  fi
fi

sed -E '/^\\restrict /d;/^\\unrestrict /d' "$SEED_FILE" > "$MIGRATION_FILE"

echo "Seed actualizado:"
echo "- $SEED_FILE"
echo "- $MIGRATION_FILE"
