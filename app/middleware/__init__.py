"""감사 로그 미들웨어.

관리자 접근 및 민감 데이터 조회 요청을 로깅한다.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("audit")

SENSITIVE_PREFIXES = ("/api/v1/chatbot/", "/api/v1/scans/", "/api/v1/medications/", "/api/v1/health/")


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.time()
        response = await call_next(request)
        elapsed_ms = (time.time() - start) * 1000

        path = request.url.path
        is_sensitive = any(path.startswith(p) for p in SENSITIVE_PREFIXES)

        if is_sensitive or response.status_code >= 400:
            user_id = request.state.user_id if hasattr(request.state, "user_id") else "anonymous"
            logger.info(
                "method=%s path=%s status=%s user=%s ip=%s elapsed=%.0fms",
                request.method,
                path,
                response.status_code,
                user_id,
                request.client.host if request.client else "-",
                elapsed_ms,
            )

        return response
