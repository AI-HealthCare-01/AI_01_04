from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.core import config
from app.models.users import User
from app.repositories.medication_intake_repository import MedicationIntakeRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.services.health import HealthService

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(
        self,
        prescription_repo: PrescriptionRepository | None = None,
        medication_repo: MedicationIntakeRepository | None = None,
        health_service: HealthService | None = None,
    ) -> None:
        self.prescription_repo = prescription_repo or PrescriptionRepository()
        self.medication_repo = medication_repo or MedicationIntakeRepository()
        self.health_service = health_service or HealthService()

    async def get_summary(self, user: User) -> dict[str, Any]:
        """
        Dashboard 요약 정보 생성

        - recent_prescription: 최근 처방전 1건
        - remaining_medication_days: 남은 약 일수 (가장 가까운 end_date 기준)
        - today_medication_completed: 오늘 복약 모두 완료 여부
        - today_health_completed: 오늘 건강관리 달성률 100% 여부 (HealthService 연동)
        """
        try:
            return await self._get_summary_impl(user)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Dashboard get_summary failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def _get_summary_impl(self, user: User) -> dict[str, Any]:
        user_id = user.id
        today = datetime.now(config.TIMEZONE).date()

        # 1) 최근 처방전 1건
        prescriptions = await self.prescription_repo.list_by_user(user_id, limit=1)
        recent_prescription: dict[str, Any] | None = None
        if prescriptions:
            rx = prescriptions[0]
            await rx.fetch_related("drug", "disease")
            recent_prescription = {
                "id": rx.id,
                "drug_name": rx.drug.name if rx.drug else None,
                "disease_name": rx.disease.name if rx.disease else None,
                "start_date": rx.start_date.isoformat() if rx.start_date else None,
                "end_date": rx.end_date.isoformat() if rx.end_date else None,
                "dose_count": rx.dose_count,
            }

        # 2) 남은 약 일수: 유효한 처방전 중 end_date가 가장 가까운 것 기준
        remaining_medication_days = 0
        all_prescriptions = await self.prescription_repo.list_by_user(user_id, limit=50)
        future_end_dates = [
            (p.end_date - today).days for p in all_prescriptions if p.end_date and p.end_date >= today
        ]
        if future_end_dates:
            remaining_medication_days = min(future_end_dates)

        # 3) 오늘 복약 완료 여부 (intake_date 컬럼 필요 - epic4_medication 마이그레이션)
        try:
            today_logs = await self.medication_repo.list_by_intake_date(user_id, today)
        except Exception as e:
            logger.warning("list_by_intake_date failed (run epic4_medication migration?): %s", e)
            today_logs = []

        today_medication_completed = False
        if today_logs:
            today_medication_completed = all(log.status == "taken" for log in today_logs)

        # 4) 오늘 건강관리 완료 여부 (HealthService.get_day_detail rate 100%)
        today_health_completed = False
        try:
            health_day = await self.health_service.get_day_detail(user_id=user_id, date=today.isoformat())
            if health_day.get("items"):
                today_health_completed = int(health_day.get("rate", 0)) >= 100
        except Exception as e:
            logger.warning("health get_day_detail failed: %s", e)
            today_health_completed = False

        return {
            "recent_prescription": recent_prescription,
            "remaining_medication_days": remaining_medication_days,
            "today_medication_completed": today_medication_completed,
            "today_health_completed": today_health_completed,
        }