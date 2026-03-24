# 네이버 OCR API 호출 (HTTP)
# 입력: 이미지/PDF 파일 경로 or bytes
# 출력: raw JSON (네이버 응답 그대로)

import json
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.core import config
from app.integrations.ocr.exceptions import (
    OCRAuthError,
    OCRBadRequestError,
    OCRConfigError,
    OCRRateLimitError,
    OCRServerError,
    OCRTimeoutError,
)


class NaverOCRClient:
    """
    네이버 OCR API HTTP 클라이언트.

    이미지/PDF 파일을 네이버 OCR API에 전송하고 raw JSON 응답을 반환.
    """

    def __init__(self):
        self.url = config.NAVER_OCR_API_URL
        self.secret = config.NAVER_OCR_SECRET_KEY

    async def analyze_file(self, file_path: str) -> dict:
        """
        파일을 네이버 OCR API로 분석.

        Args:
            file_path (str): 분석할 이미지/PDF 파일 경로.

        Returns:
            dict: 네이버 OCR API raw JSON 응답.

        Raises:
            OCRTimeoutError: 요청 타임아웃 시.
            OCRAuthError: 401/403 인증 실패 시.
            OCRRateLimitError: 429 레이트 리미트 시.
            OCRBadRequestError: 4xx 요청 오류 시.
            OCRServerError: 5xx 서버 오류 시.
        """
        if not self.url or not self.secret:
            raise OCRConfigError("OCR config missing.")

        path = Path(file_path)
        ext = path.suffix.lower().lstrip(".")  # jpg/png/pdf

        message = {
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": 0,
            "images": [{"format": ext, "name": path.stem}],
        }

        headers = {"X-OCR-SECRET": self.secret}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                with path.open("rb") as f:
                    files: Any = {
                        "file": (path.name, f, "application/octet-stream"),
                        "message": (None, json.dumps(message), "application/json"),
                    }
                    resp = await client.post(self.url, headers=headers, files=files)
        except httpx.TimeoutException as e:
            raise OCRTimeoutError("OCR request timeout") from e

        body_text = resp.text
        body_json: dict[str, Any] | None = None
        try:
            body_json = resp.json()
        except Exception:
            body_json = None

        error_code = str((body_json or {}).get("code", "")).strip()
        error_message = str((body_json or {}).get("message", "")).strip().lower()

        if resp.status_code in (401, 403):
            raise OCRAuthError("OCR auth failed (check secret key).")
        if resp.status_code == 429 or error_code == "0025" or "rate limit" in error_message:
            raise OCRRateLimitError("OCR rate limited.")
        if 400 <= resp.status_code < 500:
            raise OCRBadRequestError(f"OCR bad request: {body_text}")
        if resp.status_code >= 500:
            raise OCRServerError("OCR server error.")

        return resp.json()
