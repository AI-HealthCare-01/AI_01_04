# 외부 API 실패(401/403/429/500) 같은 걸 서비스에서 일관되게 처리하려고 둠

from __future__ import annotations


class OCRException(Exception):
    """
    OCR 통합 예외 베이스 클래스.
    - 서비스/라우터에서는 이 예외들만 잡아서 HTTPException으로 변환하면 됨.
    """
    def __init__(self, message: str = "OCR error", *, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class OCRConfigError(OCRException):
    """환경변수/설정 누락 (URL, SECRET 등)"""


class OCRAuthError(OCRException):
    """401/403 인증 실패"""


class OCRRateLimitError(OCRException):
    """429 과금/쿼터/레이트리밋"""


class OCRBadRequestError(OCRException):
    """400~499 (인증 제외) 요청 포맷 문제"""


class OCRServerError(OCRException):
    """500~599 OCR 서버 에러"""


class OCRTimeoutError(OCRException):
    """요청 타임아웃"""


class OCRParseError(OCRException):
    """응답 파싱/구조 변화로 파싱 실패"""