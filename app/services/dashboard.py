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
from app.utils.cache import TTL_DASHBOARD, cache_get, cache_set

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

    async def _build_today_medications(self, today_logs: list) -> list[dict]:
        # taken 우선 dedup: 같은 (drug, slot) 중 taken이 있으면 taken 로그를 남김
        best: dict[tuple[str, str], Any] = {}
        for log in today_logs:
            await log.fetch_related("prescription", "prescription__drug")
            rx = log.prescription
            drug_name = rx.drug.name if rx.drug else None
            slot = log.slot_label or rx.dose_timing or "아침"
            key = (drug_name or "", slot)
            prev = best.get(key)
            if prev is None or (prev.status != "taken" and log.status == "taken"):
                best[key] = log

        result: list[dict] = []
        for log in best.values():
            rx = log.prescription
            drug_name = rx.drug.name if rx.drug else None
            slot = log.slot_label or rx.dose_timing or "아침"
            result.append(
                {
                    "id": log.id,
                    "label": slot,
                    "drug_name": drug_name,
                    "dose_amount": rx.dose_amount,
                    "dose_unit": rx.dose_unit,
                    "dose_timing": rx.dose_timing,
                    "status": log.status,
                }
            )
        return result

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
            today = datetime.now(config.TIMEZONE).date()
            cached = await cache_get("dashboard", user.id, str(today))
            if cached is not None:
                return cached

            result = await self._get_summary_impl(user)
            await cache_set("dashboard", user.id, str(today), value=result, ttl=TTL_DASHBOARD)
            return result
        except Exception as e:
            logger.exception("Dashboard get_summary failed")
            raise HTTPException(status_code=500, detail="대시보드 데이터를 불러오는 중 오류가 발생했습니다.") from e

    async def _get_recent_prescription(self, user_id: int) -> dict | None:
        prescriptions = await self.prescription_repo.list_by_user(user_id, limit=1)
        if not prescriptions:
            return None
        rx = prescriptions[0]
        await rx.fetch_related("drug", "disease")
        return {
            "id": rx.id,
            "drug_name": rx.drug.name if rx.drug else None,
            "disease_name": rx.disease.name if rx.disease else None,
            "start_date": rx.start_date.isoformat() if rx.start_date else None,
            "end_date": rx.end_date.isoformat() if rx.end_date else None,
            "dose_count": rx.dose_count,
        }

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
        recent_prescription = await self._get_recent_prescription(user_id)

        # 사용자의 모든 활성 처방전에서 고유 질환명 수집
        all_prescriptions_for_diseases = await self.prescription_repo.list_by_user(user_id, limit=50)
        disease_names: list[str] = []
        seen_disease_ids: set[int] = set()
        for p in all_prescriptions_for_diseases:
            await p.fetch_related("disease")
            if p.disease and p.disease.id not in seen_disease_ids:
                seen_disease_ids.add(p.disease.id)
                label = p.disease.name
                if p.disease.kcd_code:
                    label = f"{p.disease.kcd_code} {p.disease.name}"
                disease_names.append(label)

        # 남은 약 일수: 가장 긴 처방전 기준
        remaining_medication_days = 0
        all_prescriptions = await self.prescription_repo.list_by_user(user_id, limit=50)
        future_end_dates = [(p.end_date - today).days for p in all_prescriptions if p.end_date and p.end_date >= today]
        if future_end_dates:
            remaining_medication_days = max(future_end_dates)

        # 오늘 복약 완료 여부
        try:
            today_logs = await self.medication_repo.list_by_intake_date(user_id, today)
        except Exception as e:
            logger.warning("list_by_intake_date failed (run epic4_medication migration?): %s", e)
            today_logs = []
        today_medications = await self._build_today_medications(today_logs)
        today_medication_completed = False
        today_medication_rate = 0
        if today_medications:
            taken_cnt = sum(1 for m in today_medications if m["status"] == "taken")
            today_medication_rate = int(round(taken_cnt / len(today_medications) * 100))
            today_medication_completed = taken_cnt == len(today_medications)

        # 오늘 건강관리 완료 여부
        health_logs = await HealthChecklistLog.filter(user_id=user_id, date=today).all()
        today_health_completed = bool(health_logs) and all(lg.status == "done" for lg in health_logs)

        # 현재 활성 추천 목록 (content 중복 제거)
        active_recommendations_raw = await self.recommendation_repo.list_active_for_user(user_id)
        active_recommendations = []
        seen_contents: set[str] = set()
        for active in active_recommendations_raw:
            if getattr(active.recommendation, "status", None) == "revoked":
                continue
            content_key = (active.recommendation.content or "").strip()
            if content_key in seen_contents:
                continue
            seen_contents.add(content_key)
            active_recommendations.append(_active_rec_to_dict(active.recommendation))

        # 오늘 건강 목표 (active_recommendations 기반)
        today_health_goals = [
            {
                "id": rec["id"],
                "label": rec["content"],
                "content": rec["content"],
                "status": "pending",
            }
            for rec in active_recommendations
        ]

        return {
            "recent_prescription": recent_prescription,
            "disease_names": disease_names,
            "remaining_medication_days": remaining_medication_days,
            "today_medication_completed": today_medication_completed,
            "today_health_completed": today_health_completed,
            "active_recommendations": active_recommendations,
            "today_medication_rate": today_medication_rate,
            "today_medications": today_medications,
            "today_health_goals": today_health_goals,
        }
