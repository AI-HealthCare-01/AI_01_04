FROM python:3.13-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 1. uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. 의존성 패키지 관리 파일을 컨테이너 내부에 복사합니다.
COPY pyproject.toml uv.lock ./

# 3. 모든 그룹 설치 (app, ai 그룹 포함하여 누락 방지)
# --all-groups를 사용하여 의존성 문제를 원천 차단합니다.
RUN uv sync --group app --no-dev --frozen

# 4. 소스 코드 복사
COPY ./app ./app
COPY ./frontend ./frontend
COPY ./scripts ./scripts

# 5. 실행 명령어 수정
# 서버 실행 전 'aerich upgrade'를 실행하여 테이블 생성을 자동화합니다.
# uvicorn 실행 시 --proxy-headers 등을 추가하면 나중에 Nginx 연결 시 유리합니다.
CMD ["sh", "-c", "uv run aerich upgrade && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]