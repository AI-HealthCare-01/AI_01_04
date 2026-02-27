from __future__ import annotations

from dataclasses import dataclass
from math import ceil


class PaginationError(ValueError):
    pass


@dataclass(frozen=True)
class PageParams:
    page: int = 1
    page_size: int = 20
    max_page_size: int = 100

    def normalized(self) -> "PageParams":
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
        p = self.normalized()
        return (p.page - 1) * p.page_size

    @property
    def limit(self) -> int:
        return self.normalized().page_size


def build_page_meta(*, total: int, page: int, page_size: int) -> dict:
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
    반환: {"items": [...], "meta": {...}}
    """
    params = PageParams(page=page, page_size=page_size).normalized()
    total = len(items)
    start = params.offset
    end = start + params.limit

    return {
        "items": items[start:end],
        "meta": build_page_meta(total=total, page=params.page, page_size=params.page_size),
    }