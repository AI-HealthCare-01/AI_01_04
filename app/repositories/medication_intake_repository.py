"""
복용 기록 도메인 Repository

- MedicationIntakeLog: prescription → user 연결로 user_id 스코프 적용
- 항상 user_id 스코프: prescription이 해당 user 소유인지 검증
"""

from __future__ import annotations

from datetime import date, datetime
from datetime import date as dt_date
from typing import Any

from app.models.prescriptions import MedicationIntakeLog, Prescription


class MedicationIntakeRepository:
    def __init__(self):
        self._model = MedicationIntakeLog
        self._prescription_model = Prescription

    async def get_by_id_for_user(self, user_id: int, log_id: int) -> MedicationIntakeLog | None:
        """user_id 소유의 복용 기록만 조회 (prescription.user_id 검증)"""
        return await self._model.get_or_none(
            id=log_id,
            prescription__user_id=user_id,
        )

    async def list_by_user(
        self,
        user_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MedicationIntakeLog]:
        return (
            await self._model.filter(prescription__user_id=user_id)
            .order_by("-intake_datetime")
            .offset(offset)
            .limit(limit)
            .prefetch_related("prescription")
        )

    async def list_by_date_range(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[MedicationIntakeLog]:
        return (
            await self._model.filter(
                prescription__user_id=user_id,
                intake_datetime__gte=from_dt,
                intake_datetime__lte=to_dt,
            )
            .order_by("intake_datetime")
            .prefetch_related("prescription")
        )

    async def list_by_intake_date(
        self,
        user_id: int,
        intake_date: date,
    ) -> list[MedicationIntakeLog]:
        """특정 일자의 복용 기록 (일자별 집계용)"""
        return await self._model.filter(
            prescription__user_id=user_id,
            intake_date=intake_date,
        ).prefetch_related("prescription", "prescription__drug")

    async def list_by_prescription_for_user(
        self,
        user_id: int,
        prescription_id: int,
    ) -> list[MedicationIntakeLog]:
        """특정 처방전의 복용 기록 (user 소유 검증)"""
        return await self._model.filter(
            prescription_id=prescription_id,
            prescription__user_id=user_id,
        ).order_by("-intake_datetime")

    async def create(
        self,
        user_id: int,
        prescription_id: int,
        *,
        intake_datetime: datetime,
        status: str,
    ) -> MedicationIntakeLog | None:
        """복용 기록 생성 (prescription이 user 소유인지 검증)"""
        rx = await self._prescription_model.get_or_none(id=prescription_id, user_id=user_id)
        if not rx:
            return None
        return await self._model.create(
            prescription=rx,
            intake_datetime=intake_datetime,
            status=status,
        )
    
    async def get_or_create_for_day(
        self,
        user_id: int,
        prescription_id: int,
        *,
        intake_date: dt_date,
        slot_label: str | None,
        defaults: dict[str, Any],
    ) -> MedicationIntakeLog | None:
        rx = await self._prescription_model.get_or_none(id=prescription_id, user_id=user_id)
        if not rx:
            return None

        obj = await self._model.get_or_none(
            prescription_id=prescription_id,
            intake_date=intake_date,
            slot_label=slot_label,
        )
        if obj:
            return obj

        return await self._model.create(
            prescription=rx,
            intake_date=intake_date,
            slot_label=slot_label,
            **defaults,
        )

    async def update_status_for_user(
        self,
        user_id: int,
        log_id: int,
        *,
        status: str,
        intake_datetime: datetime | None,
    ) -> MedicationIntakeLog | None:
        obj = await self.get_by_id_for_user(user_id=user_id, log_id=log_id)
        if not obj:
            return None
        obj.status = status
        obj.intake_datetime = intake_datetime
        await obj.save()
        return obj

    async def get_or_create_log_for_day(
        self,
        user_id: int,
        prescription_id: int,
        *,
        intake_date: date,
        slot_label: str | None,
        defaults: dict[str, Any],
    ) -> MedicationIntakeLog | None:
        """
        (prescription_id, intake_date, slot_label) 기준으로 로그를 찾고 없으면 생성.
        - prescription이 user 소유인지 검증
        """
        rx = await self._prescription_model.get_or_none(id=prescription_id, user_id=user_id)
        if not rx:
            return None

        obj = await self._model.get_or_none(
            prescription_id=prescription_id,
            intake_date=intake_date,
            slot_label=slot_label,
        )
        if obj:
            return obj

        return await self._model.create(
            prescription=rx,
            intake_date=intake_date,
            slot_label=slot_label,
            **defaults,
        )

    async def update_status_for_user(
        self,
        user_id: int,
        log_id: int,
        *,
        status: str,
        intake_datetime: datetime | None,
    ) -> MedicationIntakeLog | None:
        """
        user_id 소유의 log만 업데이트
        """
        obj = await self.get_by_id_for_user(user_id=user_id, log_id=log_id)
        if not obj:
            return None

        obj.status = status
        obj.intake_datetime = intake_datetime
        await obj.save()
        return obj