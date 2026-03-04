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
        # Depends로 주입이 안 되는 환경도 있어서 안전하게 기본 생성 허용
        self._medication_service = medication_service or MedicationService()
        self._health_service = health_service or HealthService()

    async def get_summary(self, user: Any) -> dict:
        """
        Dashboard 요약 정보 생성

        - 최근 처방 / 남은 약 일수: repository 파트에서 채울 예정이라 여기선 None/0 유지
        - 오늘 복약 여부: 오늘(day detail)에서 rate==100이면 완료로 간주
        - 오늘 건강관리 여부: 오늘(day detail)에서 rate==100이면 완료로 간주
        """
        today = date.today().isoformat()

        # 오늘 복약 상태
        med_done = False
        try:
            med_day = await self._medication_service.get_day_detail(user_id=user.id, date=today)
            # items가 없으면(처방전 없음) 완료=False로 둠
            if med_day.get("items"):
                med_done = int(med_day.get("rate", 0)) >= 100
        except Exception:
            # 대시보드는 "요약"이니 한쪽 에러로 전체가 깨지지 않게 방어
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
            "recent_prescription": None,  # repository에서 채울 예정
            "remaining_medication_days": 0,  # repository에서 채울 예정
            "today_medication_completed": med_done,
            "today_health_completed": health_done,
            # (선택) 프론트가 바로 상세로 이동할 때 쓰라고 날짜도 내려주면 편함
            "today_date": today,
        }