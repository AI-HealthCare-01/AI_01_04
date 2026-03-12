"""약품 서비스.

약품명 키워드 검색을 담당한다.
"""

from __future__ import annotations

from app.repositories.drug_repository import DrugRepository


class DrugService:
    def __init__(self):
        self.drug_repo = DrugRepository()

    async def search(self, keyword: str, *, limit: int = 20) -> list[dict]:
        """약품명 키워드로 검색하여 응답 딕셔너리 목록을 반환한다.

        Args:
            keyword (str): 검색할 약품명 키워드.
            limit (int): 최대 반환 건수. 기본값 20.

        Returns:
            list[dict]: id, name, manufacturer가 담긴 딕셔너리 목록.
        """
        rows = await self.drug_repo.search_by_name(keyword, limit=limit)
        return [
            {
                "id": row.id,
                "name": row.name,
                "manufacturer": row.manufacturer,
            }
            for row in rows
        ]
