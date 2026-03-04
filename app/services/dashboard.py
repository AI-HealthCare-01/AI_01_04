from __future__ import annotations

from datetime import date
from typing import Any

from app.services.health import HealthService
from app.services.medication import MedicationService


class DashboardService:
    def __init__(
        self,
        medication_service: MedicationService | None = None,
        health_service: HealthService | None = None,
    ) -> None:
        self._medication_service = medication_service or MedicationService()
        self._health_service = health_service or HealthService()

    async def get_summary(self, user: Any) -> dict:
        """
        Dashboard 요약 정보 생성

        - recent_prescription / remaining_medication_days: repository 파트에서 채울 예정이라 여기선 placeholder 유지
        - today_medication_completed: 오늘 복약 달성률이 100%이면 True
        - today_health_completed: 오늘 건강관리 달성률이 100%이면 True
        """
        today = date.today().isoformat()

        # 오늘 복약 상태
        med_done = False
        try:
            med_day = await self._medication_service.get_day_detail(user_id=user.id, date=today)
            if med_day.get("items"):
                med_done = int(med_day.get("rate", 0)) >= 100
        except Exception:
            med_done = False

        # 오늘 건강관리 상태
        health_done = False
        try:
            health_day = await self._health_service.get_day_detail(user_id=user.id, date=today)
            if health_day.get("items"):
                health_done = int(health_day.get("rate", 0)) >= 100
        except Exception:
            health_done = False

        return {
            "recent_prescription": None,
            "remaining_medication_days": 0,
            "today_medication_completed": med_done,
            "today_health_completed": health_done,
        }