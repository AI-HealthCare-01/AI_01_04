import zoneinfo
from dataclasses import field

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """
    AI 워커 설정 클래스 (pydantic-settings 기반).

    .env 파일에서 환경변수를 자동 로드하며 타입 검증을 제공.
    """

    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))

    OPENAI_API_KEY: str = Field(default="", validation_alias=AliasChoices("OPENAI_API_KEY", "api_key"))
    OPENAI_MODEL: str = "gpt-4o-mini"
