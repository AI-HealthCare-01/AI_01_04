import logging
import sys


def setup_logger(
    name: str = "AI Worker",
    level: int = logging.INFO,
) -> logging.Logger:
    """
    AI 워커 로거 설정 및 반환.

    중복 핸들러 방지 로직 포함.

    Args:
        name (str): 로거 이름. 기본값 ``AI Worker``.
        level (int): 로그 레벨. 기본값 ``logging.INFO``.

    Returns:
        logging.Logger: 설정된 Logger 인스턴스.
    """
    _logger = logging.getLogger(name)

    # 중복 핸들러 방지 (중요)
    if _logger.handlers:
        return _logger

    _logger.setLevel(level)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")

    # 콘솔 출력
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    _logger.addHandler(console_handler)
    _logger.propagate = False  # root logger로 중복 전달 방지

    return _logger
