"""처방전 도메인 Repository.

처방전 조회/생성/메모 추가를 담당한다.
항상 user_id 스코프로 다른 사용자 데이터 접근을 차단한다.
"""

from __future__ import annotations

from datetime import date, datetime

from app.models.prescriptions import Prescription, PrescriptionMemo


class PrescriptionRepository:
    def __init__(self):
        self._model = Prescription
        self._memo_model = PrescriptionMemo

    async def get_by_id_for_user(self, user_id: int, prescription_id: int) -> Prescription | None:
        """user_id 소유의 처방전을 단건 조회한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            prescription_id (int): 조회할 처방전 ID.

        Returns:
            Prescription | None: Prescription 객체. 존재하지 않거나 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.get_or_none(id=prescription_id, user_id=user_id)

    async def list_by_user(
        self,
        user_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prescription]:
        """사용자의 처방전 목록을 최신순으로 조회한다.

        Args:
            user_id (int): 조회할 사용자 ID.
            limit (int): 최대 반환 건수. 기본값 100.
            offset (int): 건너뛸 건수. 기본값 0.

        Returns:
            list[Prescription]: Prescription 객체 목록 (최신순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.filter(user_id=user_id).order_by("-created_at").offset(offset).limit(limit)

    async def list_by_date_range(
        self,
        user_id: int,
        from_date: date,
        to_date: date,
    ) -> list[Prescription]:
        """기간 내 처방전 목록을 조회한다 (start_date 기준).

        Args:
            user_id (int): 조회할 사용자 ID.
            from_date (date): 조회 시작일 (포함).
            to_date (date): 조회 종료일 (포함).

        Returns:
            list[Prescription]: 기간 내 Prescription 객체 목록 (start_date 오름차순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """처방전과 연관 데이터를 함께 조회한다 (disease, drug, memos, intake_logs prefetch).

        Args:
            user_id (int): 소유자 사용자 ID.
            prescription_id (int): 조회할 처방전 ID.

        Returns:
            Prescription | None: 연관 데이터가 prefetch된 Prescription 객체. 없으면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """처방전을 생성한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            disease_id (int | None): 질병 ID. 선택 사항.
            drug_id (int | None): 약품 ID. 선택 사항.
            dose_count (int | None): 1일 복용 횟수. 선택 사항.
            dose_amount (str | None): 1회 복용량 (예: "1정"). 선택 사항.
            dose_unit (str | None): 복용 단위 (예: "정", "ml"). 선택 사항.
            start_date (date | None): 복용 시작일. 선택 사항.
            end_date (date | None): 복용 종료일. 선택 사항.

        Returns:
            Prescription: 생성된 Prescription 객체.

        Raises:
            IntegrityError: FK 제약 위반 시 (존재하지 않는 drug_id, disease_id 등).
            OperationalError: DB 연결 오류 시.
        """
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
        """처방전에 복약 메모를 추가한다 (효과/부작용).

        소유자 검증 후 생성하며, 처방전이 없거나 소유자가 다르면 None을 반환한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            prescription_id (int): 메모를 추가할 처방전 ID.
            memo_datetime (datetime): 메모 작성 시각.
            effect (str | None): 복약 효과. 선택 사항.
            side_effect (str | None): 부작용. 선택 사항.

        Returns:
            PrescriptionMemo | None: 생성된 PrescriptionMemo 객체. 처방전이 없으면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        rx = await self.get_by_id_for_user(user_id, prescription_id)
        if not rx:
            return None
        return await self._memo_model.create(
            prescription=rx,
            memo_datetime=memo_datetime,
            effect=effect,
            side_effect=side_effect,
        )
