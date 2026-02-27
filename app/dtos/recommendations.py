from typing import Literal

from pydantic import BaseModel, Field

RecommendationType = Literal["lifestyle", "medication", "warning", "followup"]


class RecommendationResponse(BaseModel):
    id: int
    recommendation_type: RecommendationType = "lifestyle"
    content: str
    score: float | None = None
    is_selected: bool = False
    rank: int | None = None


class ScanRecommendationListResponse(BaseModel):
    scan_id: int
    items: list[RecommendationResponse]


class RecommendationUpdateRequest(BaseModel):
    content: str | None = None
    is_selected: bool | None = None
    # 필요하면 frequency, duration 같은 필드 확장 가능


class RecommendationSaveResponse(BaseModel):
    scan_id: int
    saved: bool
    saved_count: int = Field(ge=0)
