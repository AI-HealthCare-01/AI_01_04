"""질병 도메인 Repository.

Disease 마스터 데이터 및 DiseaseGuideline 조회를 담당한다.
마스터 데이터이므로 user_id 스코프가 불필요하다.
"""

from __future__ import annotations

from app.models.diseases import Disease, DiseaseCodeMapping, DiseaseGuideline


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

    async def get_by_kcd_code(self, kcd_code: str) -> Disease | None:
        """
        KCD 코드로 질환을 조회한다.

        Args:
            kcd_code (str):
                질병 코드

        Returns:
            Disease | None:
                조회된 질환 객체
        """
        return await self._model.get_or_none(kcd_code=kcd_code)

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

    async def get_mapping_by_code(self, code: str) -> DiseaseCodeMapping | None:
        """상세 KCD 코드로 매핑 레코드를 조회한다."""
        return await DiseaseCodeMapping.get_or_none(code=code.strip().upper())

    async def resolve_anchor_code(self, code: str) -> tuple[str, str] | None:
        """상세 KCD 코드를 anchor 코드로 변환한다.

        DB 매핑 테이블을 먼저 조회하고, 없으면 prefix를 줄여가며 탐색한다.

        Returns:
            (anchor_code, anchor_name) 또는 None
        """
        upper = code.strip().upper()
        if not upper:
            return None

        # 1) DB exact match
        mapping = await DiseaseCodeMapping.get_or_none(code=upper)
        if mapping:
            return mapping.mapped_code, mapping.mapped_name

        # 2) prefix fallback: 한 글자씩 줄여가며 DB 조회
        for length in range(len(upper) - 1, 2, -1):
            prefix = upper[:length]
            mapping = await DiseaseCodeMapping.get_or_none(code=prefix)
            if mapping:
                return mapping.mapped_code, mapping.mapped_name

        return None

    async def get_guidelines_by_anchor_code(self, anchor_code: str) -> list[DiseaseGuideline]:
        """anchor 코드에 해당하는 Disease의 가이드라인을 조회한다."""
        disease = await self._model.get_or_none(kcd_code=anchor_code.strip().upper())
        if not disease:
            return []
        return await self._guideline_model.filter(disease_id=disease.id).order_by("category")

    async def resolve_disease_info(self, code_or_name: str) -> tuple[str | None, str | None, list[str]]:
        """질병코드 또는 질병명으로 (anchor_code, disease_name, guideline_texts)를 반환한다.

        챗봇 프롬프트 구성용 헬퍼.
        """
        text = code_or_name.strip()
        if not text:
            return None, None, []

        # 1) 코드 형태면 매핑 테이블 → anchor → guideline
        import re

        if re.fullmatch(r"[A-Za-z]\d{2,5}", text):
            anchor = await self.resolve_anchor_code(text)
            if anchor:
                anchor_code, anchor_name = anchor
                guidelines = await self.get_guidelines_by_anchor_code(anchor_code)
                return anchor_code, anchor_name, [gl.content for gl in guidelines]

        # 2) 이름 매칭
        disease = await self.get_by_name(text)
        if not disease:
            results = await self.list_by_name_contains(text, limit=1)
            disease = results[0] if results else None

        if disease:
            guidelines = await self.get_guidelines_by_disease(disease.id)
            return disease.kcd_code, disease.name, [gl.content for gl in guidelines]

        return None, None, []
