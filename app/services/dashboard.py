from __future__ import annotations

import logging
from datetime import datetime

from fastapi import HTTPException

from app.core import config
from app.models.health import HealthChecklistLog
from app.models.users import User
from app.repositories.medication_intake_repository import MedicationIntakeRepository
from app.repositories.prescription_repository import PrescriptionRepository

logger = logging.getLogger(__name__)


class DashboardService:
    def __init__(self):
        self.prescription_repo = PrescriptionRepository()
        self.medication_repo = MedicationIntakeRepository()

    async def get_summary(self, user: User) -> dict:
        """
        Dashboard 요약 정보 생성

        - recent_prescription: 최근 처방전 1건
        - remaining_medication_days: 남은 약 일수 (가장 가까운 end_date 기준)
        - today_medication_completed: 오늘 복약 모두 완료 여부
        - today_health_completed: 오늘 건강관리 완료 여부 (모든 체크리스트 done 시 True)
        """
        try:
            return await self._get_summary_impl(user)
        except Exception as e:
            logger.exception("Dashboard get_summary failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def _get_summary_impl(self, user: User) -> dict:
        user_id = user.id
        today = datetime.now(config.TIMEZONE).date()

        # 최근 처방전 1건
        prescriptions = await self.prescription_repo.list_by_user(user_id, limit=1)
        recent_prescription = None
        if prescriptions:
            rx = prescriptions[0]
            await rx.fetch_related("drug", "disease")
            drug_name = rx.drug.name if rx.drug else None
            disease_name = rx.disease.name if rx.disease else None
            recent_prescription = {
                "id": rx.id,
                "drug_name": drug_name,
                "disease_name": disease_name,
                "start_date": rx.start_date.isoformat() if rx.start_date else None,
                "end_date": rx.end_date.isoformat() if rx.end_date else None,
                "dose_count": rx.dose_count,
            }

        # 남은 약 일수: 유효한 처방전 중 end_date가 가장 가까운 것 기준
        remaining_medication_days = 0
        all_prescriptions = await self.prescription_repo.list_by_user(user_id, limit=50)
        future_end_dates = [(p.end_date - today).days for p in all_prescriptions if p.end_date and p.end_date >= today]
        if future_end_dates:
            remaining_medication_days = min(future_end_dates)

        # 오늘 복약 완료 여부 (intake_date 컬럼 필요 - epic4_medication 마이그레이션)
        try:
            today_logs = await self.medication_repo.list_by_intake_date(user_id, today)
        except Exception as e:
            logger.warning("list_by_intake_date failed (run epic4_medication migration?): %s", e)
            today_logs = []
        today_medication_completed = False
        if today_logs:
            all_taken = all(log.status == "taken" for log in today_logs)
            today_medication_completed = all_taken

        # 오늘 건강관리 완료 여부: 로그가 존재하고 모두 done인 경우
        health_logs = await HealthChecklistLog.filter(user_id=user_id, date=today).all()
        today_health_completed = bool(health_logs) and all(lg.status == "done" for lg in health_logs)

        return {
            "recent_prescription": recent_prescription,
            "remaining_medication_days": remaining_medication_days,
            "today_medication_completed": today_medication_completed,
            "today_health_completed": today_health_completed,
        }
