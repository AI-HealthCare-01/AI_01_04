"""
약품 도메인 Repository

- Drug 마스터 데이터 검색 담당
- user_id 스코프 불필요 (마스터 데이터)
"""

from __future__ import annotations

from app.models.drugs import Drug


class DrugRepository:
    async def search_by_name(self, keyword: str, *, limit: int = 20) -> list[Drug]:
        """약품명 키워드로 부분 일치 검색 (대소문자 구분 없음)"""
        q = keyword.strip()
        if not q:
            return []

        return await Drug.filter(name__icontains=q).order_by("name").limit(limit)
