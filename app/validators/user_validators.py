import re
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from app.core import config


def validate_password(password: str) -> str:
    """
    비밀번호 복잡도 검증.

    Args:
        password (str): 검증할 비밀번호.

    Returns:
        str: 유효한 비밀번호.

    Raises:
        ValueError: 8자 미만이거나 대문자/소문자/숫자/특수문자 중 하나라도 누락된 경우.
    """
    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")

    # 대문자를 포함하고 있는지
    if not re.search(r"[A-Z]", password):
        raise ValueError("비밀번호에는 대문자, 소문자, 특수문자, 숫자가 각 하나씩 포함되어야 합니다.")

    # 소문자를 포함하고 있는지
    if not re.search(r"[a-z]", password):
        raise ValueError("비밀번호에는 대문자, 소문자, 특수문자, 숫자가 각 하나씩 포함되어야 합니다.")

    # 숫자를 포함하고 있는지
    if not re.search(r"[0-9]", password):
        raise ValueError("비밀번호에는 대문자, 소문자, 특수문자, 숫자가 각 하나씩 포함되어야 합니다.")

    # 특수문자를 포함하고 있는지
    if not re.search(r"[^a-zA-Z0-9]", password):
        raise ValueError("비밀번호에는 대문자, 소문자, 특수문자, 숫자가 각 하나씩 포함되어야 합니다.")

    return password


def validate_phone_number(phone_number: str) -> str:
    """
    휴대폰 번호 형식 검증.

    Args:
        phone_number (str): 검증할 전화번호 (010-1234-5678, 01012345678, +821012345678 허용).

    Returns:
        str: 유효한 전화번호.

    Raises:
        ValueError: 유효하지 않은 형식인 경우.
    """
    patterns = [
        r"010-\d{4}-\d{4}",  # 010-1234-5678
        r"010\d{8}",  # 01012345678
        r"\+8210\d{8}",  # +821012345678
    ]

    if not any(re.fullmatch(p, phone_number) for p in patterns):
        raise ValueError("유효하지 않은 휴대폰 번호 형식입니다.")

    return phone_number


def validate_birthday(birthday: date | str) -> date:
    """
    생년월일 유효성 검증 (만 14세 이상).

    Args:
        birthday (date | str): 검증할 생년월일.

    Returns:
        date: 유효한 생년월일.

    Raises:
        ValueError: 날짜 형식 오류 또는 만 14세 미만인 경우.
    """
    if isinstance(birthday, str):
        try:
            birthday = date.fromisoformat(birthday)
        except ValueError as e:
            raise ValueError("올바르지 않은 날짜 형식입니다. format: YYYY-MM-DD") from e

    is_over_14 = birthday < datetime.now(tz=config.TIMEZONE).date() - relativedelta(years=14)
    if not is_over_14:
        raise ValueError("서비스 약관에 따라 만14세 미만은 회원가입이 불가합니다.")

    return birthday
