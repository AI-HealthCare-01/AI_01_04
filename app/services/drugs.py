"""
약품 서비스

- 약품명 키워드 검색 담당
"""

from __future__ import annotations

from app.repositories.drug_repository import DrugRepository


class DrugService:
    def __init__(self):
        self.drug_repo = DrugRepository()

    async def search(self, keyword: str, *, limit: int = 20) -> list[dict]:
        """약품명 키워드로 검색 후 응답 dict 목록 반환"""
        rows = await self.drug_repo.search_by_name(keyword, limit=limit)
        return [
            {
                "id": row.id,
                "name": row.name,
                "manufacturer": row.manufacturer,
            }
            for row in rows
        ]
