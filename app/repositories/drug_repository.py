"""약품 도메인 Repository.

Drug 마스터 데이터 검색을 담당한다.
마스터 데이터이므로 user_id 스코프가 불필요하다.
"""

from __future__ import annotations

from tortoise import connections

from app.models.drugs import Drug


class DrugRepository:
    async def search_by_name(self, keyword: str, *, limit: int = 20) -> list[Drug]:
        """약품명 키워드로 검색한다. istartswith 우선, icontains 폴백."""
        q = keyword.strip()
        if not q:
            return []

        results = await Drug.filter(name__istartswith=q).order_by("name").limit(limit)
        if results:
            return results
        return await Drug.filter(name__icontains=q).order_by("name").limit(limit)

    async def search_by_similarity(self, keyword: str, *, limit: int = 5, threshold: float = 0.35) -> list[Drug]:
        """괄호 앞 약품명 기준 pg_trgm similarity 검색."""
        q = keyword.strip()
        if not q:
            return []
        try:
            conn = connections.get("default")
            rows = await conn.execute_query_dict(
                "SELECT id FROM drugs "
                "WHERE similarity(split_part(name, '(', 1), $1) > $2 "
                "ORDER BY similarity(split_part(name, '(', 1), $1) DESC "
                "LIMIT $3",
                [q, threshold, limit],
            )
            if not rows:
                return []
            ids = [r["id"] for r in rows]
            return await Drug.filter(id__in=ids).all()
        except Exception:
            return []
