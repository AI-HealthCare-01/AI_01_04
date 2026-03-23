from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, cast

from fastapi import HTTPException

from app.core import config
from app.dtos.recommendations import RecommendationType
from app.models.health import HealthChecklistLog
from app.models.users import User
from app.repositories.medication_intake_repository import MedicationIntakeRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.repositories.recommendation_repository import RecommendationRepository

logger = logging.getLogger(__name__)


def _normalize_rec_type(raw: Any) -> RecommendationType:
    """
    recommendation_type 값을 대시보드 응답용 표준 타입으로 정규화한다.

    Args:
        raw (Any):
            원본 recommendation_type 값

    Returns:
        RecommendationType:
            정규화된 추천 타입
    """
    s = str(raw or "").strip().lower()

    exact_map = {
        "lifestyle": "lifestyle",
        "general_care": "lifestyle",
        "daily_care": "lifestyle",
        "self_care": "lifestyle",
        "medication": "medication",
        "medication_caution": "warning",
        "drug_caution": "warning",
        "warning": "warning",
        "caution": "warning",
        "followup": "followup",
        "follow_up": "followup",
        "follow-up": "followup",
        "monitoring": "followup",
    }

    if s in exact_map:
        return cast(RecommendationType, exact_map[s])

    if "medication" in s and "caution" in s:
        return "warning"
    if "drug" in s and "caution" in s:
        return "warning"
    if "warn" in s or "caution" in s:
        return "warning"
    if "follow" in s or "monitor" in s:
        return "followup"
    if "drug" in s or "medicine" in s or "medication" in s:
        return "medication"
    return "lifestyle"


def _active_rec_to_dict(rec: Any) -> dict[str, Any]:
    """
    Recommendation ORM 객체를 대시보드 활성 추천 응답 형태로 변환한다.

    Args:
        rec (Any):
            Recommendation ORM 객체

    Returns:
        dict[str, Any]:
            활성 추천 응답 데이터
    """
    return {
        "id": rec.id,
        "recommendation_type": _normalize_rec_type(getattr(rec, "recommendation_type", None)),
        "content": rec.content,
        "score": getattr(rec, "score", None),
        "is_selected": bool(getattr(rec, "is_selected", False)),
        "rank": getattr(rec, "rank", None),
    }


class DashboardService:
    def __init__(self):
        self.prescription_repo = PrescriptionRepository()
        self.medication_repo = MedicationIntakeRepository()
        self.recommendation_repo = RecommendationRepository()

    async def get_summary(self, user: User) -> dict:
        """
        Dashboard 요약 정보를 생성한다.

        포함 정보:
        - recent_prescription: 최근 처방전 1건
        - remaining_medication_days: 남은 약 일수
        - today_medication_completed: 오늘 복약 완료 여부
        - today_health_completed: 오늘 건강관리 완료 여부
        - active_recommendations: 현재 활성 추천 목록

        Args:
            user (User):
                인증된 사용자 객체

        Returns:
            dict:
                대시보드 요약 응답 데이터
        """
        try:
            return await self._get_summary_impl(user)
        except Exception as e:
            logger.exception("Dashboard get_summary failed")
            raise HTTPException(status_code=500, detail="대시보드 데이터를 불러오는 중 오류가 발생했습니다.") from e

    async def _get_summary_impl(self, user: User) -> dict:
        """
        대시보드 요약 정보 생성 내부 구현 함수.

        Args:
            user (User):
                인증된 사용자 객체

        Returns:
            dict:
                대시보드 요약 응답 데이터
        """
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

        # 오늘 복약 완료 여부
        try:
            today_logs = await self.medication_repo.list_by_intake_date(user_id, today)
        except Exception as e:
            logger.warning("list_by_intake_date failed (run epic4_medication migration?): %s", e)
            today_logs = []
        today_medication_completed = False
        if today_logs:
            today_medication_completed = all(log.status == "taken" for log in today_logs)

        # 오늘 건강관리 완료 여부
        health_logs = await HealthChecklistLog.filter(user_id=user_id, date=today).all()
        today_health_completed = bool(health_logs) and all(lg.status == "done" for lg in health_logs)

        # 현재 활성 추천 목록
        active_recommendations_raw = await self.recommendation_repo.list_active_for_user(user_id)
        active_recommendations = [
            _active_rec_to_dict(active.recommendation)
            for active in active_recommendations_raw
            if getattr(active.recommendation, "status", None) != "revoked"
        ]

        # 오늘 복약 스케줄
        today_medications: list[dict] = []
        for log in today_logs:
            await log.fetch_related("prescription", "prescription__drug")
            rx = log.prescription
            drug_name = rx.drug.name if rx.drug else None
            today_medications.append(
                {
                    "id": log.id,
                    "label": log.slot_label or rx.dose_timing or "아침",
                    "drug_name": drug_name,
                    "dose_amount": rx.dose_amount,
                    "dose_unit": rx.dose_unit,
                    "status": log.status,
                }
            )

        # 오늘 건강 목표 (active_recommendations 기반)
        today_health_goals: list[dict] = []
        for rec in active_recommendations:
            today_health_goals.append(
                {
                    "id": rec["id"],
                    "label": rec["content"],
                    "content": rec["content"],
                    "status": "pending",
                }
            )

        return {
            "recent_prescription": recent_prescription,
            "remaining_medication_days": remaining_medication_days,
            "today_medication_completed": today_medication_completed,
            "today_health_completed": today_health_completed,
            "active_recommendations": active_recommendations,
            "today_medications": today_medications,
            "today_health_goals": today_health_goals,
        }
