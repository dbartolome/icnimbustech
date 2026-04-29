#!/usr/bin/env bash
set -euo pipefail

# Genera .env.hostinger con valores seguros por defecto para despliegue en VPS.
# Uso:
#   ./scripts/preparar-hostinger.sh [env_file] [--force]
# Ejemplo:
#   ./scripts/preparar-hostinger.sh .env.hostinger

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-.env.hostinger}"
FORCE="${2:-}"
TARGET="$ROOT_DIR/$ENV_FILE"

if [ -f "$TARGET" ] && [ "$FORCE" != "--force" ]; then
  echo "ERROR: $ENV_FILE ya existe. Usa --force para sobrescribir."
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "ERROR: se requiere openssl para generar secretos."
  exit 1
fi

BACKEND_PORT="${BACKEND_PORT:-8033}"
FRONTEND_PORT="${FRONTEND_PORT:-3033}"
MINIO_PORT="${MINIO_PORT:-9100}"
MINIO_CONSOLE_PORT="${MINIO_CONSOLE_PORT:-9101}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
POSTGRES_USER="${POSTGRES_USER:-sgs_user}"
POSTGRES_DB="${POSTGRES_DB:-sgs_prod}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-sgs_minio}"
IA_RESEARCH_PROVIDER="${IA_RESEARCH_PROVIDER:-anthropic}"
IA_RESEARCH_MODEL="${IA_RESEARCH_MODEL:-claude-sonnet-4-20250514}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(openssl rand -base64 36 | tr -dc 'A-Za-z0-9' | head -c 32)}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-$(openssl rand -base64 36 | tr -dc 'A-Za-z0-9' | head -c 32)}"
SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 64)}"

PUBLIC_IP="${PUBLIC_IP:-}"
if [ -z "$PUBLIC_IP" ]; then
  if command -v curl >/dev/null 2>&1; then
    PUBLIC_IP="$(curl -4 -fsS ifconfig.me 2>/dev/null || true)"
  fi
fi
if [ -z "$PUBLIC_IP" ]; then
  PUBLIC_IP="127.0.0.1"
fi

NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://$PUBLIC_IP:$BACKEND_PORT}"
MINIO_PUBLIC_URL="${MINIO_PUBLIC_URL:-http://$PUBLIC_IP:$MINIO_PORT}"
ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-[\"http://$PUBLIC_IP:$FRONTEND_PORT\",\"http://localhost:$FRONTEND_PORT\"]}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"

cat > "$TARGET" <<ENVVARS
# Generado automaticamente por scripts/preparar-hostinger.sh
# Revisar y ajustar si usas dominio/HTTPS

POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB

MINIO_ACCESS_KEY=$MINIO_ACCESS_KEY
MINIO_SECRET_KEY=$MINIO_SECRET_KEY
MINIO_BUCKET=sgs-documentos
MINIO_PUBLIC_URL=$MINIO_PUBLIC_URL
MINIO_PORT=$MINIO_PORT
MINIO_CONSOLE_PORT=$MINIO_CONSOLE_PORT

OLLAMA_PORT=$OLLAMA_PORT
OLLAMA_MODEL=$OLLAMA_MODEL

IA_RESEARCH_PROVIDER=$IA_RESEARCH_PROVIDER
IA_RESEARCH_MODEL=$IA_RESEARCH_MODEL
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY
OPENAI_API_KEY=$OPENAI_API_KEY
GEMINI_API_KEY=$GEMINI_API_KEY

SECRET_KEY=$SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

BACKEND_PORT=$BACKEND_PORT
FRONTEND_PORT=$FRONTEND_PORT

NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
NEXT_PUBLIC_OLLAMA_URL=

ALLOWED_ORIGINS=$ALLOWED_ORIGINS
LOG_LEVEL=$LOG_LEVEL
ENVVARS

echo "OK: $ENV_FILE generado"
echo "API pública: $NEXT_PUBLIC_API_URL"
echo "Frontend esperado: http://$PUBLIC_IP:$FRONTEND_PORT"

echo "Siguiente paso: ./scripts/arrancar-hostinger.sh $ENV_FILE"
