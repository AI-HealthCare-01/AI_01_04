from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, UploadFile
from starlette import status

from app.dtos.scan import ScanResultUpdateRequest
from app.integrations.ocr.exceptions import (
    OCRAuthError,
    OCRError,
    OCRRateLimitError,
    OCRBadRequestError,
    OCRServerError,
    OCRTimeoutError,
)
from app.integrations.ocr.naver_ocr_client import NaverOCRClient
from app.integrations.ocr.parser import parse_ocr_result
from app.services.health import HealthService
from app.services.medication import MedicationService
from app.utils.datetime import parse_date_yyyy_mm_dd

# 임시: scan_id -> scan data
_SCAN_STORE: dict[int, dict[str, Any]] = {}


class ScanAnalysisService:
    def __init__(self):
        self.med_service = MedicationService()
        self.health_service = HealthService()
        self.ocr_client = NaverOCRClient()

    async def upload_file(self, user, file: UploadFile) -> dict:
        # TODO: 확장자/용량 검증 + 파일 저장 후 file_path 저장하는 게 정석
        scan_id = 1

        _SCAN_STORE[scan_id] = {
            "scan_id": scan_id,
            "status": "uploaded",
            "analyzed_at": None,
            # OCR/사용자 수정 결과
            "document_date": None,
            "diagnosis": None,
            "drugs": [],
            # OCR 원문(선택)
            "raw_text": None,
            "ocr_raw": None,
            # TODO: 실제로는 upload 후 file_path를 저장해야 분석 가능
            # "file_path": "...",
        }
        return {"scan_id": scan_id, "status": "uploaded"}

    async def start_analysis(self, user, scan_id: int) -> dict:
        """
        OCR 분석 시작:
        - 네이버 OCR 호출 → raw JSON 획득
        - parser로 document_date/raw_text 추출
        - _SCAN_STORE에 결과 반영
        """
        cur = await self.get_result(user, scan_id)

        # TODO: upload_file에서 file_path 저장하도록 바꾸면 여기서 가져와야 함
        file_path = cur.get("file_path")
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업로드된 파일 경로(file_path)가 없습니다. upload_file에서 파일 저장 로직을 추가하세요.",
            )

        cur["status"] = "processing"

        try:
            raw = await self.ocr_client.analyze_file(file_path=file_path)
            parsed = parse_ocr_result(raw)
        except OCRTimeoutError as e:
            cur["status"] = "failed"
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(e)) from e
        except OCRRateLimitError as e:
            cur["status"] = "failed"
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e)) from e
        except OCRAuthError as e:
            cur["status"] = "failed"
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="OCR 인증 실패") from e
        except OCRBadRequestError as e:
            cur["status"] = "failed"
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except OCRServerError as e:
            cur["status"] = "failed"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
        except OCRError as e:
            cur["status"] = "failed"
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

        # 결과 반영
        cur["status"] = "done"
        cur["analyzed_at"] = datetime.now().isoformat()

        cur["document_date"] = parsed.get("document_date")
        cur["diagnosis"] = parsed.get("diagnosis")
        cur["drugs"] = parsed.get("drugs", [])
        cur["raw_text"] = parsed.get("raw_text")
        cur["ocr_raw"] = parsed.get("ocr_raw")

        return {"scan_id": scan_id, "status": cur["status"]}

    async def get_result(self, user, scan_id: int) -> dict:
        data = _SCAN_STORE.get(scan_id)
        if not data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")
        return data

    async def update_result(self, user, scan_id: int, data: ScanResultUpdateRequest) -> dict:
        cur = await self.get_result(user, scan_id)

        if data.document_date is not None:
            parse_date_yyyy_mm_dd(data.document_date)
            cur["document_date"] = data.document_date
        if data.diagnosis is not None:
            cur["diagnosis"] = data.diagnosis
        if data.drugs is not None:
            cur["drugs"] = data.drugs

        cur["status"] = "updated"
        return cur

    async def save_result(self, user, scan_id: int) -> dict:
        cur = await self.get_result(user, scan_id)

        doc_date = cur.get("document_date")
        if not doc_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="처방/진단 날짜(document_date)가 필요합니다. 결과 화면에서 입력/수정 후 저장해주세요.",
            )

        await self.med_service.ensure_day_seed(user_id=user.id, date=doc_date)
        await self.health_service.ensure_day_seed(user_id=user.id, date=doc_date)

        cur["status"] = "saved"
        return {"scan_id": scan_id, "saved": True, "seeded_date": doc_date}
