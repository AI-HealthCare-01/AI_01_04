FROM python:3.13-slim

WORKDIR /app

# 1. uv 설치 (공식 이미지에서 복사해오는 가장 깔끔한 방법)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. 의존성 패키지 관리 파일을 컨테이너 내부에 복사합니다.
COPY pyproject.toml uv.lock ./

# 3. pyproject.toml에 명시된 의존성 패키지 중에서 'ai' 그룹만 설치합니다.
RUN uv sync --group ai --no-dev --frozen

# 4. 로컬 소스 코드를 컨테이너 내부로 복사합니다.
COPY ./ai_worker ./app

# 5. 해당 이미지를 활용하여 도커컨테이너 실행시 실행되는 명령어입니다.
# 도커가 잘 올라가는지 확인하기 위해 echo실행. echo 수행한후 종료하지 않고 대기하도록 수정.
CMD ["sh", "-c", "echo 'AI Worker started' && tail -f /dev/null"]

# 추후 ai worker에 로직이 구현된 후에는
# 실제 AI 로직이 담긴 파일(예: worker_main.py)을 실행합니다.
# uv run을 사용하면 pyproject.toml에 정의된 환경으로 실행됩니다.
# CMD ["uv", "run", "python", "-m", "app.worker_main"]