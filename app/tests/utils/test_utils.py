from datetime import date

import pytest

from app.utils.datetime import DateTimeError, date_range_inclusive, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.pagination import PageParams, PaginationError, build_page_meta, paginate_list
from app.utils.progress import rate_bucket


class TestRateBucket:
    def test_good(self):
        assert rate_bucket(80) == "good"
        assert rate_bucket(100) == "good"

    def test_warn(self):
        assert rate_bucket(50) == "warn"
        assert rate_bucket(79) == "warn"

    def test_bad(self):
        assert rate_bucket(0) == "bad"
        assert rate_bucket(49) == "bad"


class TestParseDateYyyyMmDd:
    def test_valid(self):
        assert parse_date_yyyy_mm_dd("2024-01-15") == date(2024, 1, 15)

    def test_invalid(self):
        with pytest.raises(DateTimeError):
            parse_date_yyyy_mm_dd("not-a-date")


class TestDateRangeInclusive:
    def test_single_day(self):
        d = date(2024, 1, 1)
        assert date_range_inclusive(d, d) == [d]

    def test_range(self):
        result = date_range_inclusive(date(2024, 1, 1), date(2024, 1, 3))
        assert len(result) == 3

    def test_end_before_start_raises(self):
        with pytest.raises(DateTimeError):
            date_range_inclusive(date(2024, 1, 5), date(2024, 1, 1))


class TestNormalizeFromTo:
    def test_both_none_returns_30_days(self):
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
        with pytest.raises(DateTimeError):
            normalize_from_to("2024-01-10", "2024-01-01")


class TestDayBounds:
    def test_day_bounds(self):
        from app.utils.datetime import day_bounds

        start, end = day_bounds(date(2024, 1, 15))
        assert start.date() == date(2024, 1, 15)
        assert end.date() == date(2024, 1, 16)


class TestPageParams:
    def test_offset(self):
        p = PageParams(page=2, page_size=10)
        assert p.offset == 10

    def test_limit(self):
        p = PageParams(page=1, page_size=20)
        assert p.limit == 20

    def test_max_page_size_capped(self):
        p = PageParams(page=1, page_size=200, max_page_size=100)
        assert p.normalized().page_size == 100

    def test_invalid_page_raises(self):
        with pytest.raises(PaginationError):
            PageParams(page=0).normalized()

    def test_invalid_page_size_raises(self):
        with pytest.raises(PaginationError):
            PageParams(page_size=0).normalized()


class TestBuildPageMeta:
    def test_basic(self):
        meta = build_page_meta(total=100, page=1, page_size=10)
        assert meta["total"] == 100
        assert meta["total_pages"] == 10
        assert meta["has_next"] is True
        assert meta["has_prev"] is False

    def test_last_page(self):
        meta = build_page_meta(total=10, page=1, page_size=10)
        assert meta["has_next"] is False

    def test_empty(self):
        meta = build_page_meta(total=0, page=1, page_size=10)
        assert meta["total_pages"] == 0


class TestPaginateList:
    def test_first_page(self):
        items = list(range(25))
        result = paginate_list(items, page=1, page_size=10)
        assert result["items"] == list(range(10))
        assert result["meta"]["total"] == 25

    def test_last_page(self):
        items = list(range(25))
        result = paginate_list(items, page=3, page_size=10)
        assert result["items"] == [20, 21, 22, 23, 24]
