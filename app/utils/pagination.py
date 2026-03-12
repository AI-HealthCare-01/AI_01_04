from __future__ import annotations

from dataclasses import dataclass
from math import ceil


class PaginationError(ValueError):
    """페이지네이션 파라미터 검증 실패 시 발생하는 예외."""


@dataclass(frozen=True)
class PageParams:
    """
    페이지네이션 파라미터 데이터클래스.

    Attributes:
        page: 페이지 번호 (1-based).
        page_size: 페이지당 항목 수.
        max_page_size: 허용 최대 page_size.
    """

    page: int = 1
    page_size: int = 20
    max_page_size: int = 100

    def normalized(self) -> PageParams:
        """
        page, page_size 유효성 검증 후 정규화된 PageParams 반환.

        Returns:
            PageParams: 정규화된 PageParams 인스턴스.

        Raises:
            PaginationError: page 또는 page_size가 유효하지 않은 경우.
        """
        page = int(self.page)
        page_size = int(self.page_size)

        if page < 1:
            raise PaginationError("page는 1 이상이어야 합니다.")
        if page_size < 1:
            raise PaginationError("page_size는 1 이상이어야 합니다.")
        if page_size > self.max_page_size:
            page_size = self.max_page_size

        return PageParams(page=page, page_size=page_size, max_page_size=self.max_page_size)

    @property
    def offset(self) -> int:
        """
        DB 쿼리 offset 값 계산.

        Returns:
            int: (page - 1) * page_size.
        """
        p = self.normalized()
        return (p.page - 1) * p.page_size

    @property
    def limit(self) -> int:
        """
        DB 쿼리 limit 값 반환.

        Returns:
            int: 정규화된 page_size.
        """
        return self.normalized().page_size


def build_page_meta(*, total: int, page: int, page_size: int) -> dict:
    """
    페이지네이션 메타 정보 딕셔너리 생성.

    Args:
        total (int): 전체 항목 수.
        page (int): 현재 페이지 번호.
        page_size (int): 페이지당 항목 수.

    Returns:
        dict: total, page, page_size, total_pages, has_prev, has_next 포함 딕셔너리.
    """
    total = max(int(total), 0)
    page = max(int(page), 1)
    page_size = max(int(page_size), 1)

    total_pages = ceil(total / page_size) if total else 0

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
    }


def paginate_list(items: list, *, page: int, page_size: int) -> dict:
    """
    DB 없이 list를 자를 때 쓰는 헬퍼.

    Args:
        items (list): 전체 항목 리스트.
        page (int): 페이지 번호.
        page_size (int): 페이지당 항목 수.

    Returns:
        dict: {"items": [...], "meta": {...}} 형태.
    """
    params = PageParams(page=page, page_size=page_size).normalized()
    total = len(items)
    start = params.offset
    end = start + params.limit

    return {
        "items": items[start:end],
        "meta": build_page_meta(total=total, page=params.page, page_size=params.page_size),
    }
