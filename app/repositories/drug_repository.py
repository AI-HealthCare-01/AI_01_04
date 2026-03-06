from __future__ import annotations

from app.models.drugs import Drug


class DrugRepository:
    async def search_by_name(self, keyword: str, *, limit: int = 20) -> list[Drug]:
        q = keyword.strip()
        if not q:
            return []

        return await Drug.filter(name__icontains=q).order_by("name").limit(limit)
