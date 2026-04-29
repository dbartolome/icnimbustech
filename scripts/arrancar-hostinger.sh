#!/usr/bin/env bash
set -euo pipefail

# Arranca o actualiza el stack completo en el servidor Hostinger.
#
# Uso:
#   ./scripts/arrancar-hostinger.sh [env_file]
# Ejemplo:
#   ./scripts/arrancar-hostinger.sh .env.hostinger
#
# Requiere: docker, curl
# El fichero .env.hostinger debe existir con los secretos reales.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-.env.hostinger}"
COMPOSE_FILE="$ROOT_DIR/docker-compose.hostinger.yml"

# ── Validaciones ──────────────────────────────────────────────────────────────

if [ ! -f "$ROOT_DIR/$ENV_FILE" ]; then
  echo "ERROR: no existe $ENV_FILE"
  echo "Crea el fichero desde la plantilla y rellena los secretos:"
  echo "  cp .env.hostinger.example .env.hostinger"
  exit 1
fi

for cmd in docker curl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: '$cmd' no está instalado."
    exit 1
  fi
done

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: no hay acceso al daemon de Docker."
  exit 1
fi

# ── Leer variables del env ────────────────────────────────────────────────────

OLLAMA_MODEL="$(grep '^OLLAMA_MODEL=' "$ROOT_DIR/$ENV_FILE" | cut -d= -f2 || echo 'llama3.2:3b')"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
OLLAMA_PORT="$(grep '^OLLAMA_PORT=' "$ROOT_DIR/$ENV_FILE" | cut -d= -f2 || echo '11434')"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
BACKEND_PORT="$(grep '^BACKEND_PORT=' "$ROOT_DIR/$ENV_FILE" | cut -d= -f2 || echo '8033')"
BACKEND_PORT="${BACKEND_PORT:-8033}"
FRONTEND_PORT="$(grep '^FRONTEND_PORT=' "$ROOT_DIR/$ENV_FILE" | cut -d= -f2 || echo '3033')"
FRONTEND_PORT="${FRONTEND_PORT:-3033}"
MINIO_CONSOLE_PORT="$(grep '^MINIO_CONSOLE_PORT=' "$ROOT_DIR/$ENV_FILE" | cut -d= -f2 || echo '9101')"
MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9101}"

# ── 1) Levantar infraestructura y servicios ───────────────────────────────────

echo "Levantando stack Hostinger desde $ENV_FILE..."
docker compose --env-file "$ROOT_DIR/$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

# ── 2) Descargar modelo Ollama si no está disponible ─────────────────────────

echo ""
echo "Comprobando modelo Ollama '${OLLAMA_MODEL}'..."

ollama_listo=0
for i in $(seq 1 30); do
  if curl -sf "http://localhost:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; then
    ollama_listo=1
    break
  fi
  sleep 2
done

if [ "$ollama_listo" = "1" ]; then
  if curl -sf "http://localhost:${OLLAMA_PORT}/api/tags" 2>/dev/null | grep -q "\"name\":\"${OLLAMA_MODEL}"; then
    echo "  ✓ Modelo '${OLLAMA_MODEL}' ya disponible."
  else
    echo "  ▶ Descargando modelo '${OLLAMA_MODEL}'..."
    echo "    (puede tardar varios minutos la primera vez)"
    CONTAINER_OLLAMA="$(docker compose --env-file "$ROOT_DIR/$ENV_FILE" -f "$COMPOSE_FILE" ps -q ollama 2>/dev/null || true)"
    if [ -n "$CONTAINER_OLLAMA" ]; then
      docker exec "$CONTAINER_OLLAMA" ollama pull "${OLLAMA_MODEL}" || \
        echo "  ⚠ No se pudo descargar. Hazlo manualmente:"
      echo "    docker exec \$(docker compose -f docker-compose.hostinger.yml ps -q ollama) ollama pull ${OLLAMA_MODEL}"
    fi
  fi
else
  echo "  ⚠ Ollama no responde. Descarga el modelo manualmente cuando esté listo:"
  echo "    docker exec \$(docker compose -f docker-compose.hostinger.yml ps -q ollama) ollama pull ${OLLAMA_MODEL}"
fi

# ── 3) Verificar health del backend ──────────────────────────────────────────

echo ""
echo "Esperando backend en :${BACKEND_PORT}..."
backend_ok=0
for i in $(seq 1 30); do
  if curl -sf "http://localhost:${BACKEND_PORT}/health" >/dev/null 2>&1; then
    backend_ok=1
    break
  fi
  sleep 2
done

if [ "$backend_ok" = "0" ]; then
  echo "ERROR: backend no responde en http://localhost:${BACKEND_PORT}/health"
  echo "Revisa los logs:"
  echo "  docker compose --env-file $ENV_FILE -f docker-compose.hostinger.yml logs backend"
  exit 1
fi

# ── 4) Resumen ────────────────────────────────────────────────────────────────

echo ""
docker compose --env-file "$ROOT_DIR/$ENV_FILE" -f "$COMPOSE_FILE" ps

cat <<MSG

╔══════════════════════════════════════════════════════════╗
║     SGS España — IC Stack levantado en Hostinger         ║
╠══════════════════════════════════════════════════════════╣
║  Frontend  :  http://localhost:${FRONTEND_PORT}
║  Backend   :  http://localhost:${BACKEND_PORT}
║  Health    :  http://localhost:${BACKEND_PORT}/health
╠══════════════════════════════════════════════════════════╣
║  MinIO UI  :  http://localhost:${MINIO_CONSOLE_PORT}
║  Ollama    :  http://localhost:${OLLAMA_PORT}
║  Modelo    :  ${OLLAMA_MODEL}
╠══════════════════════════════════════════════════════════╣
║  Logs:
║    docker compose --env-file $ENV_FILE -f docker-compose.hostinger.yml logs -f
╚══════════════════════════════════════════════════════════╝
MSG
