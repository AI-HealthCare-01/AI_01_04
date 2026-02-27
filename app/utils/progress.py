def rate_bucket(rate: int) -> str:
    if rate >= 80:
        return "good"
    if rate >= 50:
        return "warn"
    return "bad"