from __future__ import annotations

from pydantic import BaseModel

from app.dtos.recommendations import RecommendationResponse


class DashboardSummaryResponse(BaseModel):
    recent_prescription: dict | None
    remaining_medication_days: int
    today_medication_completed: bool
    today_health_completed: bool
    active_recommendations: list[RecommendationResponse]
    today_medications: list[dict] = []
    today_health_goals: list[dict] = []
