from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import AfterValidator

T = TypeVar("T")


def optional_after_validator(func: Callable[..., Any]) -> AfterValidator:
    """
    None인 경우 검증을 건너뜨는 AfterValidator 래퍼.

    Args:
        func (Callable[..., Any]): 매핑할 검증 함수.

    Returns:
        AfterValidator: None 허용 AfterValidator 인스턴스.
    """

    def _validate(v: T | None) -> T | None:
        return func(v) if v is not None else v

    return AfterValidator(_validate)
