"""
처방전 도메인 Repository

- 항상 user_id 스코프: 다른 사용자 데이터 조회 불가
"""

from __future__ import annotations

from datetime import date, datetime

from app.models.prescriptions import Prescription, PrescriptionMemo


class PrescriptionRepository:
    def __init__(self):
        self._model = Prescription
        self._memo_model = PrescriptionMemo

    async def get_by_id_for_user(self, user_id: int, prescription_id: int) -> Prescription | None:
        """user_id 소유의 처방전만 조회 (다른 사용자 데이터 접근 불가)"""
        return await self._model.get_or_none(id=prescription_id, user_id=user_id)

    async def list_by_user(
        self,
        user_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prescription]:
        """사용자의 처방전 목록 조회 (최신순)"""
        return await self._model.filter(user_id=user_id).order_by("-created_at").offset(offset).limit(limit)

    async def list_by_date_range(
        self,
        user_id: int,
        from_date: date,
        to_date: date,
    ) -> list[Prescription]:
        """기간 내 처방전 목록 조회 (start_date 기준)"""
        return await self._model.filter(
            user_id=user_id,
            start_date__gte=from_date,
            start_date__lte=to_date,
        ).order_by("start_date")

    async def get_with_relations_for_user(
        self,
        user_id: int,
        prescription_id: int,
    ) -> Prescription | None:
        """처방전 + disease, drug, memos, intake_logs prefetch"""
        rx = await self.get_by_id_for_user(user_id, prescription_id)
        if rx:
            await rx.fetch_related("disease", "drug", "memos", "intake_logs")
        return rx

    async def create(
        self,
        *,
        user_id: int,
        disease_id: int | None = None,
        drug_id: int | None = None,
        dose_count: int | None = None,
        dose_amount: str | None = None,
        dose_unit: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Prescription:
        """처방전 생성"""
        return await self._model.create(
            user_id=user_id,
            disease_id=disease_id,
            drug_id=drug_id,
            dose_count=dose_count,
            dose_amount=dose_amount,
            dose_unit=dose_unit,
            start_date=start_date,
            end_date=end_date,
        )

    async def add_memo(
        self,
        user_id: int,
        prescription_id: int,
        *,
        memo_datetime: datetime,
        effect: str | None = None,
        side_effect: str | None = None,
    ) -> PrescriptionMemo | None:
        """처방전에 복약 메모 추가 (효과/부작용). 소유자 검증 후 생성, 없으면 None 반환"""
        rx = await self.get_by_id_for_user(user_id, prescription_id)
        if not rx:
            return None
        return await self._memo_model.create(
            prescription=rx,
            memo_datetime=memo_datetime,
            effect=effect,
            side_effect=side_effect,
        )
