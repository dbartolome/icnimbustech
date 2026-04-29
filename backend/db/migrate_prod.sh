#!/usr/bin/env bash
# =============================================================================
# SGS España — Script de migración en producción
# Aplica todas las migraciones en orden contra la DB de producción.
#
# Uso:
#   DATABASE_URL="postgresql://user:pass@host:5432/dbname" ./migrate_prod.sh
#
# O exporta DATABASE_URL en tu entorno antes de ejecutar.
# =============================================================================

set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL no está definida."
  echo "Ejemplo: DATABASE_URL=\"postgresql://user:pass@host:5432/dbname\" ./migrate_prod.sh"
  exit 1
fi

# Compatibilidad con SQLAlchemy URL (postgresql+asyncpg://...)
PSQL_DATABASE_URL="${DATABASE_URL/postgresql+asyncpg:/postgresql:}"

MIGRATIONS_DIR="$(dirname "$0")/migrations"

echo "========================================"
echo "SGS España — Migraciones de producción"
echo "========================================"
echo ""

MIGRATIONS=(
  "001_schema_inicial.sql"
  "002_notas_voz.sql"
  "003_documentos.sql"
  "004_informes.sql"
  "005_rbac.sql"
  "0060_cross_selling.sql"
  "0061_cross_selling_seed.sql"
  "007_calidad_dato.sql"
  "008_catalogo_sgs.sql"
  "009_forecast.sql"
  "011_agentes_ia.sql"
  "012_seguimientos_scoring.sql"
  "013_coaching_calidad.sql"
  "014_ia_configuracion.sql"
  "015_ia_config_operacional.sql"
  "016_historial_documentos.sql"
  "017_plantillas.sql"
  "018_estudios_ia.sql"
  "019_documentos_cuenta.sql"
  "020_conversaciones_ia_update.sql"
  "021_perfil_forecast_backfill.sql"
  "022_contexto_ia_unificado.sql"
  "023_plantillas_informe.sql"
  "024_catalogo_backfill_minimo.sql"
  "025_ia_artefactos_unificados.sql"
  "026_objetivos_comerciales.sql"
  "027_audio_compartir.sql"
  "028_compartir_documentos.sql"
  "029_transcripcion_audio.sql"
  "030_importacion_preview_csv.sql"
  "031_supervisor_rol.sql"
  "010_seed_mvp.sql"
)

for migration in "${MIGRATIONS[@]}"; do
  file="$MIGRATIONS_DIR/$migration"
  if [ ! -f "$file" ]; then
    echo "❌  No encontrado: $file"
    exit 1
  fi
  echo "▶  Aplicando $migration..."
  psql "$PSQL_DATABASE_URL" -f "$file" -v ON_ERROR_STOP=1 --quiet
  echo "   ✓ OK"
done

echo ""
echo "✅  Todas las migraciones aplicadas correctamente."
