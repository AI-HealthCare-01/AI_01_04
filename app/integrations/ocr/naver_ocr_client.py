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
    OCRRateLimitError,
    OCRServerError,
    OCRTimeoutError,
)


class NaverOCRClient:
    def __init__(self):
        self.url = config.NAVER_OCR_API_URL
        self.secret = config.NAVER_OCR_SECRET_KEY

    async def analyze_file(self, file_path: str) -> dict:
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                with path.open("rb") as f:
                    files: Any = {
                        "file": (path.name, f, "application/octet-stream"),
                        "message": (None, json.dumps(message), "application/json"),
                    }
                    resp = await client.post(self.url, headers=headers, files=files)
        except httpx.TimeoutException as e:
            raise OCRTimeoutError("OCR request timeout") from e

        if resp.status_code in (401, 403):
            raise OCRAuthError("OCR auth failed (check secret key).")
        if resp.status_code == 429:
            raise OCRRateLimitError("OCR rate limited.")
        if 400 <= resp.status_code < 500:
            raise OCRBadRequestError(f"OCR bad request: {resp.text}")
        if resp.status_code >= 500:
            raise OCRServerError("OCR server error.")

        return resp.json()
