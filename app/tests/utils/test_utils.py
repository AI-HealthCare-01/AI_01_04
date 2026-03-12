from datetime import date

import pytest

from app.utils.datetime import DateTimeError, date_range_inclusive, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.pagination import PageParams, PaginationError, build_page_meta, paginate_list
from app.utils.progress import rate_bucket


class TestRateBucket:
    """달성률 버킷 테스트."""

    def test_good(self):
        """달성률 80 이상 시 good 반환 확인."""
        assert rate_bucket(80) == "good"
        assert rate_bucket(100) == "good"

    def test_warn(self):
        """달성률 50~79 시 warn 반환 확인."""
        assert rate_bucket(50) == "warn"
        assert rate_bucket(79) == "warn"

    def test_bad(self):
        """달성률 50 미만 시 bad 반환 확인."""
        assert rate_bucket(0) == "bad"
        assert rate_bucket(49) == "bad"


class TestParseDateYyyyMmDd:
    """YYYY-MM-DD 날짜 파싱 테스트."""

    def test_valid(self):
        assert parse_date_yyyy_mm_dd("2024-01-15") == date(2024, 1, 15)

    def test_invalid(self):
        with pytest.raises(DateTimeError):
            parse_date_yyyy_mm_dd("not-a-date")


class TestDateRangeInclusive:
    """날짜 범위 생성 테스트."""

    def test_single_day(self):
        """단일 날짜 시 리스트 크기 1 확인."""
        d = date(2024, 1, 1)
        assert date_range_inclusive(d, d) == [d]

    def test_range(self):
        """시작~종료 날짜 범위 리스트 크기 확인."""
        result = date_range_inclusive(date(2024, 1, 1), date(2024, 1, 3))
        assert len(result) == 3

    def test_end_before_start_raises(self):
        with pytest.raises(DateTimeError):
            date_range_inclusive(date(2024, 1, 5), date(2024, 1, 1))


class TestNormalizeFromTo:
    """from/to 날짜 정규화 테스트."""

    def test_both_none_returns_30_days(self):
        """둘 다 None 시 최근 30일 범위 반환 확인."""
        start, end = normalize_from_to(None, None)
        assert (end - start).days == 29

    def test_from_only(self):
        start, end = normalize_from_to("2024-01-01", None)
        assert start == date(2024, 1, 1)

    def test_to_only(self):
        start, end = normalize_from_to(None, "2024-01-30")
        assert end == date(2024, 1, 30)
        assert (end - start).days == 29

    def test_both(self):
        start, end = normalize_from_to("2024-01-01", "2024-01-10")
        assert start == date(2024, 1, 1)
        assert end == date(2024, 1, 10)

    def test_end_before_start_raises(self):
        """종료일이 시작일보다 빠를 때 DateTimeError 발생 확인."""
        with pytest.raises(DateTimeError):
            normalize_from_to("2024-01-10", "2024-01-01")


class TestDayBounds:
    """day_bounds 테스트."""

    def test_day_bounds(self):
        from app.utils.datetime import day_bounds

        start, end = day_bounds(date(2024, 1, 15))
        assert start.date() == date(2024, 1, 15)
        assert end.date() == date(2024, 1, 16)


class TestPageParams:
    """PageParams 테스트."""

    def test_offset(self):
        """page=2, page_size=10 시 offset=10 확인."""
        p = PageParams(page=2, page_size=10)
        assert p.offset == 10

    def test_limit(self):
        """page_size=20 시 limit=20 확인."""
        p = PageParams(page=1, page_size=20)
        assert p.limit == 20

    def test_max_page_size_capped(self):
        """page_size가 max_page_size 초과 시 max_page_size로 제한 확인."""
        p = PageParams(page=1, page_size=200, max_page_size=100)
        assert p.normalized().page_size == 100

    def test_invalid_page_raises(self):
        """page=0 시 PaginationError 발생 확인."""
        with pytest.raises(PaginationError):
            PageParams(page=0).normalized()

    def test_invalid_page_size_raises(self):
        """page_size=0 시 PaginationError 발생 확인."""
        with pytest.raises(PaginationError):
            PageParams(page_size=0).normalized()


class TestBuildPageMeta:
    """build_page_meta 테스트."""

    def test_basic(self):
        """기본 페이지 메타 생성 확인."""
        meta = build_page_meta(total=100, page=1, page_size=10)
        assert meta["total"] == 100
        assert meta["total_pages"] == 10
        assert meta["has_next"] is True
        assert meta["has_prev"] is False

    def test_last_page(self):
        """마지막 페이지 슬라이싱 확인."""
        """마지막 페이지 시 has_next=False 확인."""
        meta = build_page_meta(total=10, page=1, page_size=10)
        assert meta["has_next"] is False

    def test_empty(self):
        """total=0 시 total_pages=0 확인."""
        meta = build_page_meta(total=0, page=1, page_size=10)
        assert meta["total_pages"] == 0


class TestPaginateList:
    """paginate_list 테스트."""

    def test_first_page(self):
        """첫 페이지 슬라이싱 확인."""
        items = list(range(25))
        result = paginate_list(items, page=1, page_size=10)
        assert result["items"] == list(range(10))
        assert result["meta"]["total"] == 25

    def test_last_page(self):
        """마지막 페이지 슬라이싱 확인."""
        """마지막 페이지 시 has_next=False 확인."""
        items = list(range(25))
        result = paginate_list(items, page=3, page_size=10)
        assert result["items"] == [20, 21, 22, 23, 24]
