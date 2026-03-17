# scripts 폴더 가이드

각 스크립트의 용도, 사용 시점, 실행 방법을 정리한 문서입니다.

---

## 1. init-db/01-pgvector.sql

### 용도
PostgreSQL에 **pgvector 확장**을 설치합니다.  
벡터 임베딩 유사도 검색(RAG, 추천 등)에 사용되는 `vector_documents.embedding` 컬럼에서 필요합니다.

### 동작 방식
```
CREATE EXTENSION IF NOT EXISTS vector;
```
- PostgreSQL이 처음 기동될 때만 실행됩니다.
- `docker-compose.yml`에서 `./scripts/init-db`를 Postgres 컨테이너의 `/docker-entrypoint-initdb.d`에 마운트함.
- 데이터가 없는 상태에서 컨테이너가 처음 시작될 때만 init 스크립트가 실행됩니다.

### 사용 시점
- `docker compose up`으로 Postgres를 처음 띄울 때 자동 실행됨.
- 별도 실행 불필요.

---

## 2. ci/run_test.sh

### 용도
로컬에서 **테스트 실행**을 위한 스크립트입니다.

### 동작
1. `./app/tests`에 `test_*.py`가 있는지 확인
2. Postgres Docker 컨테이너가 실행 중인지 확인
3. `uv run coverage run -m pytest app` 실행
4. `uv run coverage report -m`로 커버리지 출력

### 사용 시점
- 로컬에서 테스트를 돌릴 때
- CI(GitHub Actions)는 이 스크립트를 안 쓰고, `pytest`를 직접 실행합니다.

### 실행 방법
```bash
# .env 파일이 필요함 (DB_HOST, DB_PORT 등)
chmod +x scripts/ci/run_test.sh
./scripts/ci/run_test.sh
```

### 사전 조건
- Docker에서 Postgres 실행 중: `docker compose up -d postgres`
- 프로젝트 루트에 `.env` 존재

---

## 3. ci/code_fommatting.sh

### 용도
코드 자동 포맷팅 및 린트 검사입니다.

### 동작
1. `uv run ruff check . --fix` → 자동 수정 가능한 린트 수정
2. `uv run ruff check .` → 남은 이슈 확인 (수정 불가 시 에러)
3. `uv run ruff format .` → 코드 포맷팅 적용

### 사용 시점
- 커밋 전 코드 스타일 통일
- PR 전 포맷팅 정리

### 실행 방법
```bash
chmod +x scripts/ci/code_fommatting.sh
./scripts/ci/code_fommatting.sh
```

### 참고
- CI의 `ruff format . --check`는 포맷 검사만 하고, 이 스크립트는 실제로 포맷을 적용합니다.

---

## 4. ci/check_mypy.sh

### 용도
**mypy**로 타입 검사를 수행합니다.

### 동작
- `uv run mypy .` 실행
- 타입 에러가 있으면 실패

### 사용 시점
- 타입 안정성 확인
- CI에 mypy 단계가 없을 수 있음 (현재 `checks.yml`에는 없음)

### 실행 방법
```bash
chmod +x scripts/ci/check_mypy.sh
./scripts/ci/check_mypy.sh
```

---

## 5. deployment.sh

### 용도
**EC2 배포 자동화** 스크립트입니다.  
Docker 이미지 빌드·푸시·EC2 배포까지 한 번에 처리합니다.

### 동작 순서
1. `envs/.prod.env` 로드
2. Docker Hub 로그인 (username, PAT 입력)
3. Docker 레포지토리 이름 입력
4. 배포할 이미지 선택 (1: fastapi, 2: ai_worker)
5. 선택한 이미지 빌드·푸시
6. SSH 키 파일명, EC2 IP 입력
7. HTTP/HTTPS 선택
8. EC2에 `.env`, `docker-compose.prod.yml` 복사
9. SSH로 EC2 접속 후 `docker compose up -d` 실행

### 사용 시점
- 실제 배포 시
- AWS EC2 인스턴스가 준비된 상태에서만 사용

### 실행 방법
```bash
chmod +x scripts/deployment.sh
./scripts/deployment.sh
```

### 사전 조건
- Docker Hub 계정
- EC2 인스턴스 및 SSH 키
- `envs/.prod.env` 설정
- `nginx/prod_http.conf`, `nginx/prod_https.conf` 존재

---

## 6. certbot.sh

### 용도
**Let's Encrypt SSL 인증서 발급** 및 HTTPS 적용입니다.

### 동작 순서
1. `envs/.prod.env` 로드
2. 도메인, 이메일, SSH 키, EC2 IP 입력
3. `prod_http.conf`의 `server_name`을 도메인으로 수정 후 EC2에 복사
4. EC2에서 certbot 컨테이너로 SSL 인증서 발급
5. HTTPS 적용 여부 선택 (Y/N)
6. Y: `prod_https.conf` 수정 후 EC2에 복사, Nginx 재시작, certbot 재발급 서비스 실행

### 사용 시점
- 도메인 연결 후 HTTPS 적용
- `deployment.sh`로 HTTP 배포 후, HTTPS로 전환할 때

### 실행 방법
```bash
chmod +x scripts/certbot.sh
./scripts/certbot.sh
```

### 사전 조건
- EC2에 도메인 DNS A 레코드 연결
- 도메인 80번 포트가 EC2로 접근 가능

---

## 요약 표

| 파일 | 용도 | 사용 시점 |
|------|------|-----------|
| **init-db/01-pgvector.sql** | pgvector 확장 설치 | Postgres 최초 기동 시 (자동) |
| **ci/run_test.sh** | 로컬 테스트 실행 | 개발 중 테스트 |
| **ci/code_fommatting.sh** | Ruff 포맷팅·린트 | 커밋/PR 전 |
| **ci/check_mypy.sh** | mypy 타입 검사 | 타입 검증 필요 시 |
| **deployment.sh** | EC2 배포 | 실제 배포 |
| **certbot.sh** | SSL 인증서 발급 | HTTPS 적용 |

---

## 개발 단계별 사용 권장

| 단계 | 사용할 스크립트 |
|------|-----------------|
| 로컬 개발 | (없음) |
| 테스트 | `run_test.sh` |
| 커밋 전 | `code_fommatting.sh` |
| 배포 | `deployment.sh` → `certbot.sh` |
