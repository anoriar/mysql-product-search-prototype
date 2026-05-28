#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <prototype_code>"
  echo "Example: $0 p1_current"
  exit 1
fi

PROTOTYPE_CODE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
PROTOTYPE_DIR="${PROJECT_ROOT}/prototypes/${PROTOTYPE_CODE}"
ENV_FILE="${PROJECT_ROOT}/.env"

MY_CNF_FILE="${PROTOTYPE_DIR}/my.cnf"
MIGRATION_FILE="${PROTOTYPE_DIR}/migration.sql"
LOAD_SCRIPT="${PROTOTYPE_DIR}/load.py"
QUERY_DIR="${PROTOTYPE_DIR}/query"
QUERY_TEXT_FILE="${QUERY_DIR}/search_products.sql"
QUERY_PARAM_FILE="${QUERY_DIR}/search_products_with_param_score.sql"
YML_FILE="${PROJECT_ROOT}/data/products.yml"

if [ ! -d "${PROTOTYPE_DIR}" ]; then
  echo "Prototype not found: ${PROTOTYPE_CODE}"
  echo "Expected directory: ${PROTOTYPE_DIR}"
  exit 1
fi

for required_file in "${MY_CNF_FILE}" "${MIGRATION_FILE}" "${LOAD_SCRIPT}" "${QUERY_TEXT_FILE}" "${QUERY_PARAM_FILE}"; do
  if [ ! -f "${required_file}" ]; then
    echo "Missing required file for ${PROTOTYPE_CODE}: ${required_file}"
    exit 1
  fi
done

if [ -f "${ENV_FILE}" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

DB_NAME="${MYSQL_DATABASE:-ai_rec_db}"
DB_ROOT_USER="${MYSQL_ROOT_USER:-root}"
DB_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-root}"
DB_HOST="${MYSQL_HOST:-127.0.0.1}"
DB_PORT="${MYSQL_PORT:-3306}"

echo "Starting MySQL for prototype ${PROTOTYPE_CODE}..."
MYSQL_CONF_FILE="${MY_CNF_FILE}" docker compose -f "${COMPOSE_FILE}" up -d mysql --build --force-recreate

echo "Waiting for MySQL healthcheck..."
for _ in $(seq 1 60); do
  if MYSQL_CONF_FILE="${MY_CNF_FILE}" docker compose -f "${COMPOSE_FILE}" exec -T mysql \
    mysqladmin ping -h localhost -u"${DB_ROOT_USER}" -p"${DB_ROOT_PASSWORD}" --silent >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! MYSQL_CONF_FILE="${MY_CNF_FILE}" docker compose -f "${COMPOSE_FILE}" exec -T mysql \
  mysqladmin ping -h localhost -u"${DB_ROOT_USER}" -p"${DB_ROOT_PASSWORD}" --silent >/dev/null 2>&1; then
  echo "MySQL is not healthy after timeout."
  exit 1
fi

echo "Resetting database ${DB_NAME}..."
MYSQL_CONF_FILE="${MY_CNF_FILE}" docker compose -f "${COMPOSE_FILE}" exec -T mysql mysql \
  -u"${DB_ROOT_USER}" \
  -p"${DB_ROOT_PASSWORD}" \
  -e "DROP DATABASE IF EXISTS \`${DB_NAME}\`; CREATE DATABASE \`${DB_NAME}\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo "Applying migration from ${MIGRATION_FILE}..."
MYSQL_CONF_FILE="${MY_CNF_FILE}" docker compose -f "${COMPOSE_FILE}" exec -T mysql mysql \
  -u"${DB_ROOT_USER}" \
  -p"${DB_ROOT_PASSWORD}" \
  "${DB_NAME}" < "${MIGRATION_FILE}"

PYTHON_BIN="python3.11"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

echo "Loading data using ${LOAD_SCRIPT}..."
MYSQL_HOST="${DB_HOST}" \
MYSQL_PORT="${DB_PORT}" \
MYSQL_USER="${DB_ROOT_USER}" \
MYSQL_PASSWORD="${DB_ROOT_PASSWORD}" \
MYSQL_DATABASE="${DB_NAME}" \
"${PYTHON_BIN}" "${LOAD_SCRIPT}" --file "${YML_FILE}"

echo "Done. Prototype ${PROTOTYPE_CODE} is ready."
echo "Query files:"
echo "- ${QUERY_TEXT_FILE}"
echo "- ${QUERY_PARAM_FILE}"
