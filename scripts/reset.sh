#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
MIGRATION_FILE="${PROJECT_ROOT}/migrations/001_create_ai_rec_products.sql"
YML_FILE="${PROJECT_ROOT}/data/products.yml"
LOADER_SCRIPT="${PROJECT_ROOT}/scripts/load_yml_to_mysql.py"
REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements.txt"
ENV_FILE="${PROJECT_ROOT}/.env"

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

DB_NAME="${MYSQL_DATABASE:-ai_rec_db}"
DB_USER="${MYSQL_ROOT_USER:-root}"
DB_PASSWORD="${MYSQL_ROOT_PASSWORD:-root}"
DB_HOST="${MYSQL_HOST:-127.0.0.1}"
DB_PORT="${MYSQL_PORT:-3306}"

echo "Resetting database ${DB_NAME}..."
docker compose -f "${COMPOSE_FILE}" exec -T mysql mysql \
  -u"${DB_USER}" \
  -p"${DB_PASSWORD}" \
  -e "DROP DATABASE IF EXISTS \`${DB_NAME}\`; CREATE DATABASE \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo "Applying migration..."
docker compose -f "${COMPOSE_FILE}" exec -T mysql mysql \
  -u"${DB_USER}" \
  -p"${DB_PASSWORD}" \
  "${DB_NAME}" < "${MIGRATION_FILE}"

PYTHON_BIN="python3.11"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

echo "Loading YML products into ${DB_NAME}.products and ${DB_NAME}.product_attributes..."
MYSQL_HOST="${DB_HOST}" \
MYSQL_PORT="${DB_PORT}" \
MYSQL_USER="${DB_USER}" \
MYSQL_PASSWORD="${DB_PASSWORD}" \
MYSQL_DATABASE="${DB_NAME}" \
"${PYTHON_BIN}" "${LOADER_SCRIPT}" --file "${YML_FILE}"

echo "Done: database reset, migration applied, YML loaded."
