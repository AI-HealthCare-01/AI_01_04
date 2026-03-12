"""복용 기록 도메인 Repository.

MedicationIntakeLog 조회/생성/업데이트를 담당한다.
MedicationIntakeLog는 Prescription을 통해 user_id 스코프가 적용되므로
항상 prescription이 해당 user 소유인지 검증한다.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

from app.models.prescriptions import MedicationIntakeLog, Prescription


class MedicationIntakeRepository:
    def __init__(self):
        self._model = MedicationIntakeLog
        self._prescription_model = Prescription

    async def get_by_id_for_user(self, user_id: int, log_id: int) -> MedicationIntakeLog | None:
        """user_id 소유의 복용 기록을 단건 조회한다 (prescription.user_id 검증).

        Args:
            user_id (int): 소유자 사용자 ID.
            log_id (int): 조회할 복용 기록 ID.

        Returns:
            MedicationIntakeLog | None: MedicationIntakeLog 객체. 없거나 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """사용자의 복용 기록 목록을 최신순으로 조회한다.

        Args:
            user_id (int): 조회할 사용자 ID.
            limit (int): 최대 반환 건수. 기본값 100.
            offset (int): 건너뛸 건수. 기본값 0.

        Returns:
            list[MedicationIntakeLog]: prescription이 prefetch된 MedicationIntakeLog 목록 (최신순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """기간 내 복용 기록 목록을 조회한다 (intake_datetime 기준).

        Args:
            user_id (int): 조회할 사용자 ID.
            from_dt (datetime): 조회 시작 시각 (포함).
            to_dt (datetime): 조회 종료 시각 (포함).

        Returns:
            list[MedicationIntakeLog]: 기간 내 MedicationIntakeLog 목록 (시간 오름차순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """특정 일자의 복용 기록 목록을 조회한다 (일자별 집계용).

        Args:
            user_id (int): 조회할 사용자 ID.
            intake_date (date): 조회할 복용 일자.

        Returns:
            list[MedicationIntakeLog]: 해당 일자의 MedicationIntakeLog 목록.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.filter(
            prescription__user_id=user_id,
            intake_date=intake_date,
        ).prefetch_related("prescription", "prescription__drug")

    async def list_by_prescription_for_user(
        self,
        user_id: int,
        prescription_id: int,
    ) -> list[MedicationIntakeLog]:
        """특정 처방전의 복용 기록 목록을 조회한다 (user 소유 검증).

        Args:
            user_id (int): 소유자 사용자 ID.
            prescription_id (int): 조회할 처방전 ID.

        Returns:
            list[MedicationIntakeLog]: MedicationIntakeLog 목록 (최신순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """복용 기록을 생성한다 (prescription이 user 소유인지 검증).

        Args:
            user_id (int): 소유자 사용자 ID.
            prescription_id (int): 처방전 ID.
            intake_datetime (datetime): 복용 시각.
            status (str): 복용 상태 (taken, skipped, delayed).

        Returns:
            MedicationIntakeLog | None: 생성된 MedicationIntakeLog 객체. 처방전 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        rx = await self._prescription_model.get_or_none(id=prescription_id, user_id=user_id)
        if not rx:
            return None
        return await self._model.create(
            prescription=rx,
            intake_datetime=intake_datetime,
            status=status,
        )

    async def get_or_create_log_for_day(
        self,
        user_id: int,
        prescription_id: int,
        *,
        intake_date: date,
        slot_label: str | None,
        defaults: dict[str, Any],
    ) -> MedicationIntakeLog | None:
        """(prescription_id, intake_date, slot_label) 기준으로 로그를 조회하고 없으면 생성한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            prescription_id (int): 처방전 ID.
            intake_date (date): 복용 일자.
            slot_label (str | None): 복용 슬롯 (아침/점심/저녁/자기전).
            defaults (dict[str, Any]): 생성 시 사용할 기본값 딕셔너리.

        Returns:
            MedicationIntakeLog | None: 조회 또는 생성된 MedicationIntakeLog 객체. 처방전 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
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
        """user_id 소유의 복용 기록 상태를 업데이트한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            log_id (int): 업데이트할 복용 기록 ID.
            status (str): 새 복용 상태 (taken, skipped, delayed).
            intake_datetime (datetime | None): 복용 시각. taken이면 현재 시각, 해제면 None.

        Returns:
            MedicationIntakeLog | None: 업데이트된 MedicationIntakeLog 객체. 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        obj = await self.get_by_id_for_user(user_id=user_id, log_id=log_id)
        if not obj:
            return None

        obj.status = status

        # mypy가 intake_datetime을 datetime(non-optional)로 보는 환경이 있어 우회
        obj_any = cast(Any, obj)
        obj_any.intake_datetime = intake_datetime

        await obj.save()
        return obj
