"""약품 도메인 Repository.

Drug 마스터 데이터 검색을 담당한다.
마스터 데이터이므로 user_id 스코프가 불필요하다.
"""

from __future__ import annotations

from app.models.drugs import Drug


class DrugRepository:
    async def search_by_name(self, keyword: str, *, limit: int = 20) -> list[Drug]:
        """약품명 키워드로 부분 일치 검색한다 (대소문자 구분 없음).

        Args:
            keyword (str): 검색할 약품명 키워드.
            limit (int): 최대 반환 건수. 기본값 20.

        Returns:
            list[Drug]: 검색된 Drug 객체 목록. 키워드가 빈 문자열이면 빈 목록 반환.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        q = keyword.strip()
        if not q:
            return []

        return await Drug.filter(name__icontains=q).order_by("name").limit(limit)
