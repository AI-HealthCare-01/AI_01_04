from typing import Literal

from pydantic import BaseModel, Field

Bucket = Literal["good", "warn", "bad", "none"]
MedicationStatus = Literal["taken", "skipped", "delayed"]


class PageMeta(BaseModel):
    """페이지네이션 메타 정보."""

    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)
    has_prev: bool
    has_next: bool


class MedicationHistoryRow(BaseModel):
    """복약 이력 일자별 요약 행."""

    date: str
    rate: int = Field(ge=0, le=100)
    bucket: Bucket
    detail_key: str


class MedicationHistoryListResponse(BaseModel):
    """복약 이력 목록 응답 스키마."""

    items: list[MedicationHistoryRow]
    meta: PageMeta


class MedicationChecklistItem(BaseModel):
    """복약 체크리스트 단일 항목."""

    id: int
    label: str
    status: MedicationStatus
    intake_datetime: str | None = None


class MedicationDayDetailResponse(BaseModel):
    """특정 일자 복약 상세 응답 스키마."""

    date: str
    rate: int = Field(ge=0, le=100)
    bucket: Bucket
    items: list[MedicationChecklistItem]


class MedicationLogUpdateRequest(BaseModel):
    """복약 로그 상태 업데이트 요청 스키마."""

    status: MedicationStatus


class MedicationLogUpdateResponse(BaseModel):
    """복약 로그 업데이트 응답 스키마."""

    log_id: int
    updated: bool
    day: MedicationDayDetailResponse
