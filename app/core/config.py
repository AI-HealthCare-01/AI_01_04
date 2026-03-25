import os
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    """애플리케이션 실행 환경 열거형."""

    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    """
    애플리케이션 설정 클래스 (pydantic-settings 기반).

    .env 파일에서 환경변수를 자동 로드하며 타입 검증을 제공.
    """

    model_config = SettingsConfigDict(env_file="envs/.local.env", env_file_encoding="utf-8", extra="ignore")

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = ""
    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")
    FILE_STORAGE_DIR: str = "./artifacts"

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = "ai_health"
    DB_CONNECT_TIMEOUT: int = 5
    DB_CONNECTION_POOL_MAXSIZE: int = 30

    COOKIE_DOMAIN: str = "localhost"
    CORS_ORIGINS: str = ""

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5

    NAVER_OCR_SECRET_KEY: str = ""
    NAVER_OCR_API_URL: str = ""
    OPENAI_API_KEY: str = Field(default="", validation_alias=AliasChoices("OPENAI_API_KEY", "api_key"))
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ENABLE_LLM_REFINEMENT=False로 검증 그다음 LLM refinement 켜서 비교
    ENABLE_LLM_REFINEMENT: bool = False
