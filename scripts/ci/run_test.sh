set -eo pipefail

COLOR_GREEN=$(tput setaf 2)
COLOR_BLUE=$(tput setaf 4)
COLOR_RED=$(tput setaf 1)
COLOR_NC=$(tput sgr0)

cd "$(dirname "$0")/../.."

source .env

echo "${COLOR_BLUE}Find Tests${COLOR_NC}"

HAS_TESTS=false
POSTGRES_CONTAINER_NAME=postgres

if [ -d "./app/tests" ] && find ./app/tests -name 'test_*.py' -print -quit | read ; then
  HAS_TESTS=true
fi

echo "Has tests: $HAS_TESTS"

if [ "$HAS_TESTS" = true ]; then
  if docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER_NAME}$"; then
    echo "${COLOR_BLUE}→ PostgreSQL container found. Running tests with PostgreSQL...${COLOR_NC}"

    # test DB 및 기본 DB 준비 (없으면 생성)
    docker exec ${POSTGRES_CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -tc "SELECT 1 FROM pg_database WHERE datname='test'" | grep -q 1 || \
      docker exec ${POSTGRES_CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "CREATE DATABASE test;"
    docker exec ${POSTGRES_CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -tc "SELECT 1 FROM pg_database WHERE datname='${DB_USER}'" | grep -q 1 || \
      docker exec ${POSTGRES_CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "CREATE DATABASE ${DB_USER};"
    docker exec ${POSTGRES_CONTAINER_NAME} psql -U ${DB_USER} -d test -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

    echo "${COLOR_BLUE}Run Pytest with Coverage${COLOR_NC}"

    if ! TEST_DB=postgres uv run coverage run -m pytest app; then
      echo ""
      echo "${COLOR_RED}✖ Pytest failed.${COLOR_NC}"
      echo "${COLOR_RED}→ Fix the test failures above and re-run.${COLOR_NC}"
      exit 1
    fi

    echo "${COLOR_BLUE}Coverage Report${COLOR_NC}"
    if ! uv run coverage report -m ; then
      echo "${COLOR_RED}✖ Coverage check failed.${COLOR_NC}"
      exit 1
    fi
  else
    echo "${COLOR_RED}PostgreSQL Docker Container Not Found. Run docker compose up postgres.${COLOR_NC}"
  fi
else
  echo "${COLOR_BLUE}No tests found. Skipping tests.${COLOR_NC}"
fi
