import asyncio
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import Mock, patch

import pytest
import pytest_asyncio
from _pytest.fixtures import FixtureRequest
from tortoise import generate_config
from tortoise.contrib.test import finalizer, initializer

from app.core import config
from app.db.databases import TORTOISE_APP_MODELS

TEST_BASE_URL = "http://test"
TEST_DB_LABEL = "models"
TEST_DB_TZ = "Asia/Seoul"


def get_test_db_url() -> str:
    """
    환경에 따라 테스트 DB 선택 (하이브리드 방식)

    - 로컬 개발: SQLite (빠름)
    - 통합 테스트: PostgreSQL (정확함)
    - CI/CD: PostgreSQL (자동)
    """
    # CI 환경 또는 명시적으로 PostgreSQL 요청
    if os.getenv("CI") or os.getenv("TEST_DB") == "postgres":
        return f"postgres://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/test"

    # 기본값: SQLite (메모리)
    return "sqlite://:memory:"


def get_test_db_config() -> dict[str, Any]:
    db_url = get_test_db_url()
    print(f"\n🗄️  Test DB: {db_url.split('://')[0].upper()}")

    tortoise_config = generate_config(
        db_url=db_url,
        app_modules={TEST_DB_LABEL: TORTOISE_APP_MODELS},
        connection_label=TEST_DB_LABEL,
        testing=True,
    )
    tortoise_config["timezone"] = TEST_DB_TZ

    return tortoise_config


@pytest.fixture(scope="session", autouse=True)
def initialize(request: FixtureRequest) -> Generator[None, None]:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    with patch("tortoise.contrib.test.getDBConfig", Mock(return_value=get_test_db_config())):
        initializer(modules=TORTOISE_APP_MODELS)
    yield
    finalizer()
    loop.close()


@pytest_asyncio.fixture(autouse=True, scope="session")  # type: ignore[type-var]
def event_loop() -> None:
    pass
