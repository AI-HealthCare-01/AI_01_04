# MySQL → PostgreSQL + pgvector 마이그레이션 변경사항

## 개요

벡터 임베딩 검색(vector_documents) 지원을 위해 MySQL에서 PostgreSQL + pgvector로 전환했습니다.

---

## 1. Docker Compose

### docker-compose.yml, docker-compose.prod.yml

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 서비스명 | `mysql` | `postgres` |
| 이미지 | `mysql:8.0` | `pgvector/pgvector:pg16` |
| 컨테이너명 | `mysql` | `postgres` |
| 환경변수 | `MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| 포트 매핑 | `${DB_EXPOSE_PORT}:${DB_PORT}` (3306) | `${DB_EXPOSE_PORT}:5432` |
| 볼륨 | `mysql_data:/var/lib/mysql` | `postgres_data:/var/lib/postgresql/data` |
| command | utf8mb4 문자셋 설정 | 제거 (PostgreSQL 기본 UTF-8) |
| healthcheck | `mysqladmin ping` | `pg_isready -U ${DB_USER} -d ${DB_NAME}` |
| init 스크립트 | 없음 | `./scripts/init-db:/docker-entrypoint-initdb.d` |
| depends_on | `mysql` | `postgres` |
| volumes | `mysql_data` | `postgres_data` |
| fastapi/ai-worker environment | - | `DB_HOST: postgres` (Docker 내부 접속용, .env 덮어씀) |

---

## 2. 환경 변수 (.env, envs/.local.env, envs/.prod.env)

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| DB_PORT | 3306 | 5432 |
| DB_EXPOSE_PORT | 3306 | 5432 |
| DB_ROOT_PASSWORD | 있음 | **제거** (PostgreSQL은 POSTGRES_USER가 관리자) |
| DB_HOST (.prod.env) | mysql | postgres |

---

## 3. 애플리케이션 코드

### app/db/databases.py

```diff
- "engine": "tortoise.backends.mysql",
- "dialect": "asyncmy",
+ "engine": "tortoise.backends.asyncpg",
- "connect_timeout": config.DB_CONNECT_TIMEOUT,
```

> `connect_timeout` 제거: asyncpg는 해당 옵션을 지원하지 않습니다.

### app/core/config.py

```diff
- DB_PORT: int = 3306
+ DB_PORT: int = 5432
```

### app/tests/conftest.py

```diff
- db_url=f"mysql://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/test",
+ db_url=f"postgres://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/test",
```

---

## 4. 의존성 (pyproject.toml)

```diff
- "asyncmy>=0.2.11",
+ "asyncpg>=0.30.0",
```

---

## 5. CI 스크립트

### scripts/ci/run_test.sh

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 컨테이너명 | `MYSQL_CONTAINER_NAME=mysql` | `POSTGRES_CONTAINER_NAME=postgres` |
| 권한 부여 | `mysql -u root` 로 GRANT 실행 | **제거** (PostgreSQL은 사용자 생성 시 권한 부여됨) |
| 에러 메시지 | "Run docker compose up mysql" | "Run docker compose up postgres" |

### .github/workflows/checks.yml

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 서비스 | `mysql: mysql:8.0` | `postgres: pgvector/pgvector:pg16` |
| 환경변수 | MYSQL_* | POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB |
| 포트 | 3306 | 5432 |
| 추가 | - | `env:` (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME) |
| 추가 | - | pgvector 확장 초기화 단계 |

---

## 6. 신규 파일

### scripts/init-db/01-pgvector.sql

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

컨테이너 최초 기동 시 pgvector 확장을 활성화합니다.

---

## 7. 마이그레이션 참고사항

- **기존 MySQL 데이터**: 새 PostgreSQL 볼륨으로 시작하므로 기존 데이터는 이전되지 않습니다.
- **aerich 마이그레이션**: MySQL용 마이그레이션은 PostgreSQL과 호환되지 않습니다. `app/db/migrations/` 초기화 후 `uv run aerich init-db` 로 새로 생성하는 것을 권장합니다.
- **DB_HOST**: `.env`는 `DB_HOST=localhost`로 두면 됩니다. Docker Compose 실행 시 `docker-compose.yml`의 `environment`에서 자동으로 `DB_HOST=postgres`로 덮어씁니다. (수동 변경 불필요)

---

## 8. 확인 방법

```bash
# 의존성 설치
uv sync --group app

# PostgreSQL 기동
docker compose up -d postgres redis

# 마이그레이션 (최초 1회, 기존 migrations 삭제 후)
rm -rf app/db/migrations/models/*
uv run aerich init-db
# (이후 모델 변경 시) uv run aerich migrate --name 변경내용
# uv run aerich upgrade

# 테스트
./scripts/ci/run_test.sh

# 로컬 서버 실행
uv run uvicorn app.main:app --reload
```

---

## 9. 마이그레이션 후 수정사항 (FastAPI 호환)

FastAPI 최신 버전에서 `Query()` 기본값 설정 방식이 변경되었습니다.

### health_router.py, medication_router.py

```diff
- date_from: Annotated[str | None, Query(None, alias="from")] = None,
- date_to: Annotated[str | None, Query(None, alias="to")] = None,
+ date_from: Annotated[str | None, Query(alias="from")] = None,
+ date_to: Annotated[str | None, Query(alias="to")] = None,
```

`Query()` 내부에 기본값을 넣지 않고, `= None`으로만 설정합니다.
