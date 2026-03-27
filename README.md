# MEDIMATE — AI 헬스케어 서비스

처방전/진료기록지를 스캔하면 AI가 분석하여 복약 일정과 건강관리 목표를 자동 생성하는 서비스입니다.
FastAPI 백엔드 + 바닐라 JS 프론트엔드 + PostgreSQL(pgvector) + Redis + Nginx 스택으로 구성됩니다.

---

## 핵심 원칙

- 의료 데이터 안전: 민감정보는 서버에서만 처리, 프론트에 PII 노출 최소화
- AI 결과 신뢰성: 4단계 fallback(AI → 가이드라인 → 벡터 유사도 → 기본 메시지)으로 항상 결과 반환
- 비동기 분리: 무거운 OCR/GPT 처리는 HTTP 202 + Background Task로 API 응답과 분리
- 외부 API 방어: OpenAI/네이버 OCR 호출에 15초 timeout + 자동 재시도 + graceful fallback

---

## 주요 기능

- **처방전/진료기록지 OCR 분석**: 네이버 OCR + OpenAI 후처리로 진단명·약물·용법 자동 추출
- **AI 건강관리 추천**: 진단+가이드라인+약물정보 기반 맞춤 건강 목표 생성
- **복약 관리**: 처방전 기반 일별 복약 슬롯 자동 생성 및 이행 추적
- **건강 체크리스트**: 일상 건강관리 항목 체크 및 달성률 추적
- **대시보드**: 복약 완료율, 건강관리 달성률, 활성 추천 목록 한눈에 확인
- **AI 챗봇**: LangChain + OpenAI 기반 건강/복약 상담
- **약물 상호작용 경고**: 프론트엔드에서 병용 주의 약물 조합 실시간 표시
- **약물 검색**: pg_trgm 유사도 + 벡터 유사도 기반 다단계 매칭

---

## 디렉터리 구조

```text
.
├── app/                    # FastAPI 백엔드
│   ├── apis/v1/            # API 라우터 (인증, 스캔, 추천, 복약, 건강, 대시보드, 챗봇, 약물, 질병)
│   ├── core/               # 설정 (pydantic-settings), 로거
│   ├── db/                 # Tortoise ORM 초기화, Aerich 마이그레이션
│   ├── dependencies/       # JWT 인증 의존성
│   ├── dtos/               # 요청/응답 Pydantic 모델
│   ├── integrations/       # 외부 API 연동
│   │   ├── ocr/            # 네이버 OCR 클라이언트 + OpenAI 후처리
│   │   └── openai/         # OpenAI ChatCompletion / Embedding 클라이언트
│   ├── models/             # DB 테이블 정의 (Tortoise ORM)
│   ├── repositories/       # 데이터 접근 계층
│   ├── services/           # 비즈니스 로직 (스캔분석, 추천, 복약, 건강, 대시보드, 챗봇)
│   ├── utils/              # 공통 유틸 (캐시, 날짜, 파일, 페이지네이션, 보안)
│   ├── validators/         # 입력 검증
│   ├── tests/              # Pytest 테스트
│   └── main.py             # FastAPI 앱 진입점
├── ai_worker/              # AI 모델 추론 워커 (별도 컨테이너)
├── frontend/               # 바닐라 JS + Bootstrap 프론트엔드
│   ├── css/style.css
│   ├── js/                 # api.js, components.js, utils.js, texts.js, chat-widget.js
│   ├── dashboard.html      # 대시보드
│   ├── scans.html          # 문서 업로드 + OCR 분석
│   ├── scan_result.html    # 분석 결과 확인/수정/저장 + 건강 목표 추천
│   ├── medications.html    # 복약 관리 이력
│   ├── health.html         # 건강 관리 이력
│   ├── chatbot.html        # AI 챗봇
│   ├── profile.html        # 내 프로필
│   └── index.html          # 로그인/회원가입
├── scripts/
│   ├── ci/                 # CI 스크립트 (테스트, 포맷팅, 타입체크)
│   ├── init-db/            # DB 초기화 (pgvector, pg_trgm, 시드 데이터)
│   ├── deployment.sh       # EC2 자동 배포
│   └── certbot.sh          # SSL 인증서 자동 발급
├── envs/                   # 환경 변수 (.local.env, .prod.env)
├── nginx/                  # Nginx 설정 (HTTP/HTTPS 리버스 프록시)
├── docs/                   # 구현 보고서 및 가이드
├── docker-compose.yml      # 로컬 개발용 전체 스택
├── docker-compose.prod.yml # 프로덕션 배포용
└── pyproject.toml          # uv 기반 의존성 관리
```

---

## 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | FastAPI, Tortoise ORM, Aerich (마이그레이션) |
| 데이터베이스 | PostgreSQL 16 + pgvector + pg_trgm |
| 캐싱 | Redis (약물 검색 24h, 추천 30m, 대시보드 30s) |
| AI/ML | OpenAI GPT-4o-mini, text-embedding-3-small, LangChain |
| OCR | 네이버 CLOVA OCR |
| 프론트엔드 | 바닐라 JS + Bootstrap 5 |
| 인프라 | Docker Compose, Nginx, AWS EC2 |
| CI/CD | GitHub Actions (Ruff lint + Pytest + Coverage) |
| 패키지 관리 | uv |

---

## 사전 준비

- Python 3.13+
- uv ([설치 가이드](https://github.com/astral-sh/uv))
- Docker & Docker Compose
- (선택) 네이버 OCR API 키, OpenAI API 키

---

## 설치 및 설정

### 1. 의존성 설치

```bash
uv sync               # 전체 의존성
uv sync --group app   # API 서버용
uv sync --group ai    # AI 워커용
```

### 2. 환경 변수 설정

```bash
cp envs/example.local.env envs/.local.env   # 로컬용
cp envs/example.prod.env envs/.prod.env     # 배포용
```

`.local.env` 필수 항목:

| 변수 | 설명 |
|---|---|
| `SECRET_KEY` | JWT 서명 키 |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | PostgreSQL 접속 정보 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `NAVER_OCR_SECRET_KEY` | 네이버 OCR 시크릿 키 |
| `NAVER_OCR_API_URL` | 네이버 OCR API 엔드포인트 |
| `REDIS_URL` | Redis 접속 URL (기본: `redis://localhost:6379/0`) |

---

## 실행 방법

### Docker Compose (권장)

```bash
docker-compose up -d --build
```

실행 후 접속:
- 웹: http://localhost (Nginx → 프론트엔드)
- API Swagger: http://localhost/api/docs
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

종료:
```bash
docker-compose down
```

### 로컬 개별 실행 (개발용)

```bash
# FastAPI 서버
uv run uvicorn app.main:app --reload

# AI Worker
uv run python -m ai_worker.main
```

---

## API 구현 범위

### 인증
- 이메일/비밀번호 회원가입, 로그인, 로그아웃
- JWT Access Token + Cookie Refresh Token
- 회원 탈퇴 (soft delete)

### 스캔 분석 (OCR + AI)
- `POST /api/v1/scans/upload` — 의료문서 업로드 (201)
- `POST /api/v1/scans/{scan_id}/analyze` — OCR 분석 시작 (202 Accepted, Background Task)
- `GET /api/v1/scans/{scan_id}` — 분석 결과 조회 (polling)
- `PATCH /api/v1/scans/{scan_id}/result` — 결과 수정
- `POST /api/v1/scans/{scan_id}/save` — 처방전/복약 시스템 반영

### 건강관리 추천
- `GET /api/v1/recommendations/scans/{scan_id}` — scan 기반 추천 조회/생성
- `GET /api/v1/recommendations/active` — 활성 추천 목록
- `PATCH /api/v1/recommendations/{id}` — 추천 수정
- `DELETE /api/v1/recommendations/{id}` — 추천 삭제 (soft)
- `POST /api/v1/recommendations/scans/{scan_id}/save` — 활성 추천으로 등록
- `POST /api/v1/recommendations/{id}/feedback` — 피드백 (like/dislike/click)

### 복약 관리
- `GET /api/v1/medications/history` — 기간별 복약 이력 (달성률 포함)
- `PATCH /api/v1/medications/logs/{log_id}` — 복약 상태 변경 (taken/skipped/delayed)

### 건강 관리
- `GET /api/v1/health/history` — 기간별 건강관리 이력
- `PATCH /api/v1/health/logs/{log_id}` — 건강관리 상태 변경 (done/skipped)

### 대시보드
- `GET /api/v1/dashboard/summary` — 종합 요약 (처방전, 복약률, 건강관리, 활성 추천)

### AI 챗봇
- `POST /api/v1/chatbot/chat` — LangChain 기반 건강/복약 상담
- `GET /api/v1/chatbot/history/{patient_id}` — 상담 이력
- `GET /api/v1/chatbot/context/{user_id}` — 사용자 컨텍스트

### 약물/질병 검색
- `GET /api/v1/drugs/search?q=` — 약물명 검색 (다단계 매칭)
- `GET /api/v1/diseases/search?q=` — 질병명/KCD코드 검색

---

## 성능 최적화

### 비동기 처리
- OCR/AI 분석은 `HTTP 202 Accepted` + `BackgroundTasks`로 API 응답과 분리
- 프론트엔드는 polling으로 진행 상태 추적 (단계별 progress indicator)

### 캐싱 (Redis)
- 약물 검색: TTL 24시간 (마스터 데이터)
- 추천 결과: TTL 30분
- 대시보드 요약: TTL 30초 (상태 변경 시 즉시 무효화)
- Redis 연결 실패 시 graceful degradation (캐시 없이 정상 동작)

### DB 최적화
- pgvector HNSW 인덱스: 벡터 유사도 검색 O(n) → O(log n)
- pg_trgm: 약물명 유사도 검색
- Tortoise ORM 비동기 쿼리 + Connection Pool

### AI 응답 최적화
- OpenAI 호출에 `max_tokens` 출력 제한 (OCR: 2048, 추천: 1024)
- 입력 데이터 truncate (약물 5개, 필드 100자)
- 외부 API timeout 15초 + 1회 자동 재시도

### UX
- Skeleton UI (데이터 로딩 중 레이아웃 유지)
- 단계별 Progress Indicator (OCR 분석 중 실시간 안내)
- 이미지 리사이징 최적화 (업로드 전 2000px, JPEG 85%)
- 약물 상호작용 실시간 경고

---

## EC2 배포 (Production)

### 사전 준비
- EC2 인스턴스 (Ubuntu 권장)
- SSH 키 페어
- Docker Hub 계정 및 Personal Access Token
- 배포용 환경 변수 (`envs/.prod.env`)
- 도메인 (Route53, Gabia 등)

### 자동 배포

```bash
chmod +x scripts/deployment.sh
./scripts/deployment.sh
```

입력 항목:
1. Docker Hub 계정 정보
2. 레포지토리 이름
3. 배포 서비스 선택 (FastAPI / AI-Worker) 및 버전 태그
4. SSH 키 파일명 및 EC2 IP
5. HTTPS 사용 여부 (도메인 입력)

### SSL 설정

```bash
chmod +x scripts/certbot.sh
./scripts/certbot.sh
```

Let's Encrypt 인증서 자동 발급 + Nginx 설정 갱신

---

## 테스트 및 품질 관리

```bash
# 테스트 실행
./scripts/ci/run_test.sh

# 코드 포맷팅 (Ruff)
./scripts/ci/code_fommatting.sh

# 정적 타입 검사 (Mypy)
./scripts/ci/check_mypy.sh
```

GitHub Actions CI:
- push/PR 시 자동 실행 (main, develop, release/*, hotfix/*)
- Ruff lint + format check → Pytest + Coverage

---

## 개발 가이드

- **API 추가**: `app/apis/v1/`에 라우터 생성 → `app/apis/v1/__init__.py`에 등록
- **DB 모델 추가**: `app/models/`에 Tortoise 모델 정의 → `app/db/databases.py`의 `TORTOISE_APP_MODELS`에 추가
- **서비스 로직 추가**: `app/services/`에 비즈니스 로직 → `app/repositories/`에 데이터 접근 분리
- **AI 로직 추가**: `ai_worker/tasks/`에 처리 로직 → `ai_worker/main.py`에서 호출
- **시드 데이터**: `scripts/init-db/`에 SQL/CSV/JSON 추가 → docker-compose 초기화 시 자동 실행

---

## 참고 문서

- [MySQL → PostgreSQL 마이그레이션](docs/01MIGRATION_MYSQL_TO_POSTGRESQL.md)
- [Repository 패턴 구현 보고서](docs/02T2-2_REPOSITORY_IMPLEMENTATION_REPORT.md)
- [스크립트 가이드](docs/03SCRIPTS_GUIDE.md)
- [서비스 레이어 통합 보고서](docs/04SERVICE_LAYER_INTEGRATION_REPORT.md)
- [테스트 환경 설정 가이드](docs/05TEST_SETUP_GUIDE.md)
