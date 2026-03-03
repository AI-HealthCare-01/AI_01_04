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
        return await self._model.get_or_none(id=disease_id)

    async def list_all(self) -> list[Disease]:
        return await self._model.all()

    async def get_with_guidelines(self, disease_id: int) -> Disease | None:
        disease = await self._model.get_or_none(id=disease_id)
        if disease:
            await disease.fetch_related("guidelines")
        return disease

    async def list_by_ids(self, ids: list[int]) -> list[Disease]:
        if not ids:
            return []
        return await self._model.filter(id__in=ids)

    async def get_guidelines_by_disease(self, disease_id: int) -> list[DiseaseGuideline]:
        return await self._guideline_model.filter(disease_id=disease_id).order_by("category")
