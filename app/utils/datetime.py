from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.core import config


class DateTimeError(ValueError):
    pass


def today_kst() -> date:
    return datetime.now(tz=config.TIMEZONE).date()


def parse_date_yyyy_mm_dd(value: str) -> date:
    """
    'YYYY-MM-DD' 문자열을 date로 파싱
    """
    try:
        return date.fromisoformat(value)
    except Exception as e:
        raise DateTimeError("올바르지 않은 날짜 형식입니다. format: YYYY-MM-DD") from e


def date_range_inclusive(start: date, end: date) -> list[date]:
    """
    start~end 포함한 date 리스트 생성
    """
    if end < start:
        raise DateTimeError("to는 from보다 빠를 수 없습니다.")
    days = (end - start).days
    return [start + timedelta(days=i) for i in range(days + 1)]


def normalize_from_to(date_from: str | None, date_to: str | None) -> tuple[date, date]:
    """
    Query로 들어오는 from/to 문자열을 안전하게 date 범위로 변환
    - 둘 다 없으면: 최근 30일(오늘 포함)
    - from만 있으면: from~오늘
    - to만 있으면: (to-29일)~to
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
    특정 날짜의 [00:00:00, 다음날 00:00:00) 범위를 KST datetime으로 반환
    DB에서 하루치 로그 조회할 때 유용
    """
    start = datetime.combine(dt_date, time.min, tzinfo=config.TIMEZONE)
    end = start + timedelta(days=1)
    return start, end
