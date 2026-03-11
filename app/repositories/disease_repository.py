"""질병 도메인 Repository.

Disease 마스터 데이터 및 DiseaseGuideline 조회를 담당한다.
마스터 데이터이므로 user_id 스코프가 불필요하다.
"""

from __future__ import annotations

from app.models.diseases import Disease, DiseaseGuideline


class DiseaseRepository:
    def __init__(self):
        self._model = Disease
        self._guideline_model = DiseaseGuideline

    async def get_by_id(self, disease_id: int) -> Disease | None:
        """ID로 질병을 단건 조회한다.

        Args:
            disease_id (int): 조회할 질병 ID.

        Returns:
            Disease | None: Disease 객체. 존재하지 않으면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.get_or_none(id=disease_id)

    async def list_all(self) -> list[Disease]:
        """전체 질병 목록을 조회한다.

        Returns:
            list[Disease]: 전체 Disease 객체 목록.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.all()

    async def get_with_guidelines(self, disease_id: int) -> Disease | None:
        """질병과 연관된 가이드라인을 함께 조회한다.

        Args:
            disease_id (int): 조회할 질병 ID.

        Returns:
            Disease | None: guidelines가 prefetch된 Disease 객체. 존재하지 않으면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        disease = await self._model.get_or_none(id=disease_id)
        if disease:
            await disease.fetch_related("guidelines")
        return disease

    async def list_by_ids(self, ids: list[int]) -> list[Disease]:
        """ID 목록으로 질병 목록을 조회한다.

        Args:
            ids (list[int]): 조회할 질병 ID 목록.

        Returns:
            list[Disease]: 해당 ID의 Disease 객체 목록. ids가 비어있으면 빈 목록 반환.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        if not ids:
            return []
        return await self._model.filter(id__in=ids)

    async def get_guidelines_by_disease(self, disease_id: int) -> list[DiseaseGuideline]:
        """특정 질병의 가이드라인 목록을 조회한다 (category 오름차순).

        Args:
            disease_id (int): 조회할 질병 ID.

        Returns:
            list[DiseaseGuideline]: DiseaseGuideline 객체 목록.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._guideline_model.filter(disease_id=disease_id).order_by("category")
