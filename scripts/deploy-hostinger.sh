#!/usr/bin/env bash
set -euo pipefail

# Despliegue para servidor Hostinger desde código versionado en GitHub.
# Uso:
#   ./scripts/deploy-hostinger.sh [rama] [env_file]
# Ejemplo:
#   ./scripts/deploy-hostinger.sh main .env.hostinger

BRANCH="${1:-main}"
ENV_FILE="${2:-.env.hostinger}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.hostinger.yml"

if [ ! -f "$ROOT_DIR/$ENV_FILE" ]; then
  echo "No existe $ENV_FILE. Generando automaticamente..."
  "$ROOT_DIR/scripts/preparar-hostinger.sh" "$ENV_FILE"
fi

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git no está instalado."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker no está instalado."
  exit 1
fi

cd "$ROOT_DIR"

echo "Sincronizando rama $BRANCH..."
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "Levantando stack Docker..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

echo "Comprobando health backend..."
BACKEND_PORT="$(grep '^BACKEND_PORT=' "$ENV_FILE" | cut -d= -f2 || true)"
BACKEND_PORT="${BACKEND_PORT:-8033}"
curl -fsS "http://localhost:${BACKEND_PORT}/health" >/dev/null

echo "Despliegue OK en Hostinger"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
