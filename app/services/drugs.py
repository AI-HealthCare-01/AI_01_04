"""약품 서비스.

약품명 키워드 검색을 담당한다.
"""

from __future__ import annotations

from app.repositories.drug_repository import DrugRepository


class DrugService:
    def __init__(self):
        self.drug_repo = DrugRepository()

    async def search(self, keyword: str, *, limit: int = 20) -> list[dict]:
        """약품명 키워드로 검색하여 응답 딕셔너리 목록을 반환한다."""
        rows = await self.drug_repo.search_by_name(keyword, limit=limit)
        if not rows:
            corrected = self._correct_ocr_typo(keyword)
            if corrected != keyword:
                rows = await self.drug_repo.search_by_name(corrected, limit=limit)
        if not rows:
            normalized = self._normalize_unit(keyword)
            if normalized != keyword:
                rows = await self.drug_repo.search_by_name(normalized, limit=limit)
                if not rows:
                    corrected_norm = self._correct_ocr_typo(normalized)
                    if corrected_norm != normalized:
                        rows = await self.drug_repo.search_by_name(corrected_norm, limit=limit)
        return [
            {
                "id": row.id,
                "name": row.name,
                "manufacturer": row.manufacturer,
                "main_ingredient": row.main_ingredient,
                "efficacy": row.efficacy,
                "dosage": row.dosage,
                "caution": " ".join(filter(None, [row.caution_1, row.caution_2, row.caution_3, row.caution_4]))[:500] or None,
                "storage": row.storage,
            }
            for row in rows
        ]

    @staticmethod
    def _correct_ocr_typo(keyword: str) -> str:
        """OCR 오인식 보정: '점'→'정' 등 약품명에서 흔한 오타를 교정한다."""
        import re
        return re.sub(r'점(\d|$)', r'정\1', keyword)

    @staticmethod
    def _normalize_unit(keyword: str) -> str:
        """mg→밀리그램 등 단위 표기를 정규화한다."""
        import re
        result = keyword
        result = re.sub(r'(\d+)\s*mg\b', r'\1밀리그램', result, flags=re.IGNORECASE)
        result = re.sub(r'(\d+)\s*ml\b', r'\1밀리리터', result, flags=re.IGNORECASE)
        result = re.sub(r'(\d+)\s*mcg\b', r'\1마이크로그램', result, flags=re.IGNORECASE)
        result = re.sub(r'(\d+)\s*g\b', r'\1그램', result, flags=re.IGNORECASE)
        return result
