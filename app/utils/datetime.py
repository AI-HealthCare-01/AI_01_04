from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.core import config


class DateTimeError(ValueError):
    """날짜/시간 처리 실패 시 발생하는 예외."""


def today_kst() -> date:
    """
    현재 KST 기준 오늘 날짜 반환.

    Returns:
        date: KST 기준 오늘 date 객체.
    """
    return datetime.now(tz=config.TIMEZONE).date()


def parse_date_yyyy_mm_dd(value: str) -> date:
    """
    'YYYY-MM-DD' 문자열을 date로 파싱.

    Args:
        value (str): YYYY-MM-DD 형식 날짜 문자열.

    Returns:
        date: 파싱된 date 객체.

    Raises:
        DateTimeError: 날짜 형식이 올바르지 않은 경우.
    """
    try:
        return date.fromisoformat(value)
    except Exception as e:
        raise DateTimeError("올바르지 않은 날짜 형식입니다. format: YYYY-MM-DD") from e


def date_range_inclusive(start: date, end: date) -> list[date]:
    """
    start~end 포함한 date 리스트 생성.

    Args:
        start (date): 시작 날짜.
        end (date): 종료 날짜 (포함).

    Returns:
        list[date]: start부터 end까지 포함한 date 리스트.

    Raises:
        DateTimeError: end가 start보다 빠른 경우.
    """
    if end < start:
        raise DateTimeError("to는 from보다 빠를 수 없습니다.")
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


def normalize_from_to(date_from: str | None, date_to: str | None) -> tuple[date, date]:
    """
    Query로 들어오는 from/to 문자열을 안전하게 date 범위로 변환.

    Args:
        date_from (str | None): 시작일 (YYYY-MM-DD). None이면 기본값 적용.
        date_to (str | None): 종료일 (YYYY-MM-DD). None이면 기본값 적용.

    Returns:
        tuple[date, date]: (start, end) 날짜 튜플.
            - 둘 다 None: 최근 30일(오늘 포함).
            - from만 있으면: from~오늘.
            - to만 있으면: (to-29일)~to.

    Raises:
        DateTimeError: end가 start보다 빠른 경우.
    """
    if date_from is None and date_to is None:
        end = today_kst()
        start = end - timedelta(days=29)
        return start, end

    if date_from is not None:
        start = parse_date_yyyy_mm_dd(date_from)
    else:
        # to만 있을 때
        end = parse_date_yyyy_mm_dd(date_to)  # type: ignore[arg-type]
        start = end - timedelta(days=29)
        return start, end

    if date_to is not None:
        end = parse_date_yyyy_mm_dd(date_to)
    else:
        end = today_kst()

    if end < start:
        raise DateTimeError("to는 from보다 빠를 수 없습니다.")

    return start, end


def day_bounds(dt_date: date) -> tuple[datetime, datetime]:
    """
    특정 날짜의 [00:00:00, 다음날 00:00:00) 범위를 KST datetime으로 반환.

    Args:
        dt_date (date): 범위를 구할 날짜.

    Returns:
        tuple[datetime, datetime]: (start, end) KST datetime 튜플. DB에서 하루치 로그 조회 시 유용.
    """
    start = datetime.combine(dt_date, time.min, tzinfo=config.TIMEZONE)
    end = start + timedelta(days=1)
    return start, end
