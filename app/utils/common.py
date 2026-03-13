import re


def normalize_phone_number(phone_number: str) -> str:
    """
    전화번호를 01012345678 형식으로 정규화.

    Args:
        phone_number (str): +82, 하이픈 포함 다양한 형식의 전화번호.

    Returns:
        str: 숫자만 남긴 정규화된 전화번호.
    """
    if phone_number.startswith("+82"):
        phone_number = "0" + phone_number[3:]
    phone_number = re.sub(r"\D", "", phone_number)

    return phone_number
