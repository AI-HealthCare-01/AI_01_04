"""약품 서비스.

약품명 키워드 검색을 담당한다.
"""

from __future__ import annotations

from app.repositories.drug_repository import DrugRepository


class DrugService:
    def __init__(self):
        self.drug_repo = DrugRepository()

    async def _try_corrected_search(self, keyword: str, limit: int) -> list:
        corrected = self._correct_ocr_typo(keyword)
        if corrected != keyword:
            rows = await self.drug_repo.search_by_name(corrected, limit=limit)
            if rows:
                return rows
        normalized = self._normalize_unit(keyword)
        if normalized != keyword:
            rows = await self.drug_repo.search_by_name(normalized, limit=limit)
            if rows:
                return rows
            corrected_norm = self._correct_ocr_typo(normalized)
            if corrected_norm != normalized:
                rows = await self.drug_repo.search_by_name(corrected_norm, limit=limit)
                if rows:
                    return rows
        return []

    async def _search_with_fallbacks(self, keyword: str, limit: int) -> list:
        rows = await self.drug_repo.search_by_name(keyword, limit=limit)
        if rows:
            return rows
        rows = await self._try_corrected_search(keyword, limit)
        if rows:
            return rows
        core = self._extract_core_name(keyword)
        if core:
            for length in range(len(core), 1, -1):
                rows = await self.drug_repo.search_by_name(core[:length], limit=limit)
                if rows:
                    return rows
        return await self.drug_repo.search_by_similarity(keyword, limit=limit)

    async def search(self, keyword: str, *, limit: int = 20) -> list[dict]:
        """약품명 키워드로 검색하여 응답 딕셔너리 목록을 반환한다."""
        rows = await self._search_with_fallbacks(keyword, limit)
        return [
            {
                "id": row.id,
                "name": row.name,
                "manufacturer": row.manufacturer,
                "main_ingredient": row.main_ingredient,
                "efficacy": row.efficacy,
                "dosage": row.dosage,
                "caution": " ".join(filter(None, [row.caution_1, row.caution_2, row.caution_3, row.caution_4]))[:500]
                or None,
                "storage": row.storage,
            }
            for row in rows
        ]

    @staticmethod
    def _correct_ocr_typo(keyword: str) -> str:
        """OCR 오인식 보정: 약품명에서 흔한 받침/글자 혼동을 교정한다."""
        import re

        result = keyword
        # "점안액" 관련 오인식 보정 (점인액, 정인액, 정안액, 점안액 등)
        result = re.sub(r"[점정][안인]액", "점안액", result)
        # "점안" 뒤에 액이 없는 경우도 보정
        result = re.sub(r"[점정][안인](?=\s|$)", "점안", result)
        # "점" 뒤에 숫자가 오면 "정"으로 (예: "점 5mg" → "정 5mg")
        result = re.sub(r"점(\d)", r"정\1", result)
        return result

    @staticmethod
    def _extract_core_name(keyword: str) -> str:
        """제형 접미사·용량·괄호를 제거하여 핵심 브랜드명을 추출한다."""
        import re

        core = re.sub(
            r"[\d.]+\s*(%|mg|ml|g|mcg|밀리그램|그램)?"
            r"|\(.*?\)"
            r"|(점안액|점안|정|캡슐|시럽|액|주사|산|현탁액|크림|겔|패취|연질캡슐)",
            "",
            keyword,
        ).strip()
        return core if len(core) >= 2 else ""

    @staticmethod
    def _normalize_unit(keyword: str) -> str:
        """mg→밀리그램 등 단위 표기를 정규화한다."""
        import re

        result = keyword
        result = re.sub(r"(\d+)\s*mg\b", r"\1밀리그램", result, flags=re.IGNORECASE)
        result = re.sub(r"(\d+)\s*ml\b", r"\1밀리리터", result, flags=re.IGNORECASE)
        result = re.sub(r"(\d+)\s*mcg\b", r"\1마이크로그램", result, flags=re.IGNORECASE)
        result = re.sub(r"(\d+)\s*g\b", r"\1그램", result, flags=re.IGNORECASE)
        return result
