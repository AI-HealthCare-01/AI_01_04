class TokenBackendError(Exception):
    """토큰 백엔드 처리 실패 시 발생하는 기본 예외."""


class TokenBackendExpiredError(TokenBackendError):
    """토큰 만료 시 발생하는 예외."""


class TokenError(Exception):
    """토큰 처리 실패 시 발생하는 기본 예외."""


class ExpiredTokenError(TokenError):
    """만료된 토큰 사용 시 발생하는 예외."""
