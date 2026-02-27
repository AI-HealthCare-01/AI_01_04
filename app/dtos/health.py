from typing import Literal

from pydantic import BaseModel, Field

Bucket = Literal["good", "warn", "bad", "none"]
HealthStatus = Literal["done", "skipped"]


class HealthHistoryRow(BaseModel):
    date: str
    rate: int = Field(ge=0, le=100)


class HealthHistoryListResponse(BaseModel):
    items: list[HealthHistoryRow]


class HealthChecklistItem(BaseModel):
    id: int
    label: str  # 예: "물 마시기", "걷기", ...
    status: HealthStatus


class HealthDayDetailResponse(BaseModel):
    date: str
    rate: int = Field(ge=0, le=100)
    bucket: Bucket
    items: list[HealthChecklistItem]


class HealthLogUpdateRequest(BaseModel):
    status: HealthStatus


class HealthLogUpdateResponse(BaseModel):
    log_id: int
    updated: bool
    day: HealthDayDetailResponse
