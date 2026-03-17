from typing import Literal

from pydantic import BaseModel, Field

Bucket = Literal["good", "warn", "bad", "none"]
HealthStatus = Literal["done", "skipped"]


class HealthHistoryRow(BaseModel):
    """건강관리 이력 일자별 요약 행."""

    date: str
    rate: int = Field(ge=0, le=100)


class HealthHistoryListResponse(BaseModel):
    """건강관리 이력 목록 응답 스키마."""

    items: list[HealthHistoryRow]


class HealthChecklistItem(BaseModel):
    """건강관리 체크리스트 단일 항목."""

    id: int
    label: str
    status: HealthStatus


class HealthDayDetailResponse(BaseModel):
    """특정 일자 건강관리 상세 응답 스키마."""

    date: str
    rate: int = Field(ge=0, le=100)
    bucket: Bucket
    items: list[HealthChecklistItem]


class HealthLogUpdateRequest(BaseModel):
    """건강관리 로그 상태 업데이트 요청 스키마."""

    status: HealthStatus


class HealthLogUpdateResponse(BaseModel):
    """건강관리 로그 업데이트 응답 스키마."""

    log_id: int
    updated: bool
    day: HealthDayDetailResponse
