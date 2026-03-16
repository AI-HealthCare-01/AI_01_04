def rate_bucket(rate: int) -> str:
    """
    달성률에 따른 버킷 문자열 반환.

    Args:
        rate (int): 달성률 (0~100).

    Returns:
        str: ``good`` (≥80%), ``warn`` (≥50%), ``bad`` (<50%).
    """
    if rate >= 80:
        return "good"
    if rate >= 50:
        return "warn"
    return "bad"
