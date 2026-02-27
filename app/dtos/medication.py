from typing import Literal
from pydantic import BaseModel, Field


Bucket = Literal["good", "warn", "bad", "none"]
MedicationStatus = Literal["taken", "skipped", "delayed"]


class MedicationHistoryRow(BaseModel):
    date: str  # YYYY-MM-DD
    rate: int = Field(ge=0, le=100)


class MedicationHistoryListResponse(BaseModel):
    items: list[MedicationHistoryRow]


class MedicationChecklistItem(BaseModel):
    id: int
    label: str  # 예: "아침", "점심", "저녁", "자기전"
    status: MedicationStatus
    intake_datetime: str | None = None  # 실제 복용 시간(있으면)


class MedicationDayDetailResponse(BaseModel):
    date: str
    rate: int = Field(ge=0, le=100)
    bucket: Bucket
    items: list[MedicationChecklistItem]


class MedicationLogUpdateRequest(BaseModel):
    status: MedicationStatus


class MedicationLogUpdateResponse(BaseModel):
    log_id: int
    updated: bool
    day: MedicationDayDetailResponse