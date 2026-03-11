from __future__ import annotations

from pydantic import BaseModel

from app.dtos.recommendations import RecommendationResponse


class DashboardSummaryResponse(BaseModel):
    """
    대시보드 요약 응답 스키마.

    Attributes:
        recent_prescription (dict | None):
            최근 처방전 요약 정보
        remaining_medication_days (int):
            남은 약 일수
        today_medication_completed (bool):
            오늘 복약 완료 여부
        today_health_completed (bool):
            오늘 건강관리 완료 여부
        active_recommendations (list[RecommendationResponse]):
            현재 활성 추천 목록
    """

    recent_prescription: dict | None
    remaining_medication_days: int
    today_medication_completed: bool
    today_health_completed: bool
    active_recommendations: list[RecommendationResponse]