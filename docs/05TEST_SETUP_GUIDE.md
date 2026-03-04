# Test Setup Guide

## 🧪 하이브리드 테스트 환경

이 프로젝트는 **하이브리드 테스트 DB 전략**을 사용합니다.

---

## 📊 테스트 DB 선택

### 자동 선택 로직

```python
if os.getenv("CI") or os.getenv("TEST_DB") == "postgres":
    # PostgreSQL 사용
else:
    # SQLite 사용 (기본값)
```

---

## 🚀 사용 방법

### 1. 로컬 개발 (SQLite - 빠름)

```bash
# 기본값: SQLite 메모리 DB
pytest app/tests/

# 특정 테스트만
pytest app/tests/auth_apis/test_login_api.py

# 상세 출력
pytest app/tests/ -v
```

**특징**:
- ⚡ 빠른 속도 (5초)
- 🔧 설치 불필요
- 💻 로컬 개발에 최적

---

### 2. 통합 테스트 (PostgreSQL - 정확함)

```bash
# PostgreSQL 사용
TEST_DB=postgres pytest app/tests/

# PR 전 최종 검증
TEST_DB=postgres pytest app/tests/ -v
```

**특징**:
- ✅ 프로덕션과 동일
- 🎯 정확한 검증
- 🔍 pgvector 테스트 가능

**사전 준비**:
```bash
# PostgreSQL 실행 (Docker Compose)
docker-compose up -d postgres

# 테스트 DB 생성
docker exec -it postgres psql -U postgres -c "CREATE DATABASE test;"
```

---

### 3. CI/CD (자동 PostgreSQL)

GitHub Actions에서 자동으로 PostgreSQL 사용:

```yaml
# .github/workflows/test.yml
env:
  CI: true  # 자동으로 PostgreSQL 선택
```

---

## 📈 성능 비교

| DB | 속도 | 정확도 | 설정 |
|----|------|--------|------|
| SQLite | ⚡ 5초 | ⚠️ 95% | 불필요 |
| PostgreSQL | 🐢 30초 | ✅ 100% | 필요 |

---

## 🎯 권장 워크플로우

```bash
# 1. 개발 중 (빠른 반복)
pytest app/tests/  # SQLite

# 2. 기능 완성 후
TEST_DB=postgres pytest app/tests/  # PostgreSQL

# 3. PR 생성
# GitHub Actions가 자동으로 PostgreSQL 실행
```

---

## 🔧 설정 파일

### conftest.py

```python
def get_test_db_url() -> str:
    """환경에 따라 테스트 DB 선택"""
    if os.getenv("CI") or os.getenv("TEST_DB") == "postgres":
        return f"postgres://..."
    return "sqlite://:memory:"
```

---

## 🐛 트러블슈팅

### PostgreSQL 연결 실패

```bash
# 에러: database "test" does not exist
docker exec -it postgres psql -U postgres -c "CREATE DATABASE test;"

# 에러: connection refused
docker-compose up -d postgres
```

### SQLite 제약사항

- pgvector 사용 불가
- 일부 PostgreSQL 전용 문법 미지원
- 프로덕션과 약간의 차이 가능

---

## 📝 테스트 작성 가이드

### 기본 테스트

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_example(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
```

### DB 의존 테스트

```python
from app.models.users import User

@pytest.mark.asyncio
async def test_user_creation():
    user = await User.create(
        email="test@example.com",
        name="Test User"
    )
    assert user.id is not None
```

---

## 🎓 참고 자료

- [Tortoise ORM Testing](https://tortoise.github.io/contrib/unittest.html)
- [Pytest Async](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
