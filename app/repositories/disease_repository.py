"""
질병 도메인 Repository

- Disease: 마스터 데이터 (user_id 없음) → user 스코프 불필요
- DiseaseGuideline: 질병별 가이드라인
"""

from __future__ import annotations

from app.models.diseases import Disease, DiseaseGuideline


class DiseaseRepository:
    def __init__(self):
        self._model = Disease
        self._guideline_model = DiseaseGuideline

    async def get_by_id(self, disease_id: int) -> Disease | None:
        """
        질환 ID로 단건 조회한다.

        Args:
            disease_id (int):
                질환 ID

        Returns:
            Disease | None:
                조회된 질환 객체
        """
        return await self._model.get_or_none(id=disease_id)

    async def list_all(self) -> list[Disease]:
        """
        전체 질환 목록을 조회한다.

        Returns:
            list[Disease]:
                질환 목록
        """
        return await self._model.all()

    async def get_with_guidelines(self, disease_id: int) -> Disease | None:
        """
        질환과 연결된 guideline을 함께 조회한다.

        Args:
            disease_id (int):
                질환 ID

        Returns:
            Disease | None:
                guideline이 fetch된 질환 객체
        """
        disease = await self._model.get_or_none(id=disease_id)
        if disease:
            await disease.fetch_related("guidelines")
        return disease

    async def list_by_ids(self, ids: list[int]) -> list[Disease]:
        """
        여러 질환 ID로 목록 조회한다.

        Args:
            ids (list[int]):
                질환 ID 목록

        Returns:
            list[Disease]:
                조회된 질환 목록
        """
        if not ids:
            return []
        return await self._model.filter(id__in=ids)

    async def get_guidelines_by_disease(self, disease_id: int) -> list[DiseaseGuideline]:
        """
        특정 질환의 guideline 목록을 조회한다.

        Args:
            disease_id (int):
                질환 ID

        Returns:
            list[DiseaseGuideline]:
                guideline 목록
        """
        return await self._guideline_model.filter(disease_id=disease_id).order_by("category")

    async def get_by_icd_code(self, icd_code: str) -> Disease | None:
        """
        ICD/KCD 코드로 질환을 조회한다.

        Args:
            icd_code (str):
                질병 코드

        Returns:
            Disease | None:
                조회된 질환 객체
        """
        return await self._model.get_or_none(icd_code=icd_code)

    async def get_by_name(self, name: str) -> Disease | None:
        """
        질환명 정확 일치로 조회한다.

        Args:
            name (str):
                질환명

        Returns:
            Disease | None:
                조회된 질환 객체
        """
        return await self._model.get_or_none(name=name)

    async def list_by_name_contains(self, keyword: str, limit: int = 10) -> list[Disease]:
        """
        질환명 부분 일치로 질환 목록을 조회한다.

        Args:
            keyword (str):
                검색 키워드
            limit (int):
                최대 조회 개수

        Returns:
            list[Disease]:
                부분 일치 질환 목록
        """
        if not keyword.strip():
            return []
        return await self._model.filter(name__icontains=keyword.strip()).limit(limit)
