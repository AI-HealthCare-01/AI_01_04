from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, UploadFile
from starlette import status

from app.dtos.scan import ScanResultUpdateRequest
from app.integrations.ocr.exceptions import (
    OCRAuthError,
    OCRBadRequestError,
    OCRError,
    OCRRateLimitError,
    OCRServerError,
    OCRTimeoutError,
)
from app.integrations.ocr.naver_ocr_client import NaverOCRClient
from app.integrations.ocr.parser import parse_ocr_result
from app.models.diseases import Disease
from app.models.drugs import Drug
from app.models.prescriptions import Prescription
from app.services.health import HealthService
from app.services.medication import MedicationService
from app.utils.datetime import parse_date_yyyy_mm_dd
from app.utils.files import (
    save_user_upload_file,
)

# 임시: scan_id -> scan data
_SCAN_STORE: dict[int, dict[str, Any]] = {}


def _next_scan_id() -> int:
    return (max(_SCAN_STORE.keys()) + 1) if _SCAN_STORE else 1


class ScanAnalysisService:
    def __init__(self):
        self.med_service = MedicationService()
        self.health_service = HealthService()
        self.ocr_client = NaverOCRClient()

    async def upload_file(self, user, file: UploadFile) -> dict:
        # ✅ scan_id 자동 증가
        scan_id = _next_scan_id()

        # ✅ 파일 저장하고 file_path 확보 (임시 구현)
        file_path = await save_user_upload_file(
            user_id=user.id,
            upload=file,
        )

        _SCAN_STORE[scan_id] = {
            "scan_id": scan_id,
            "status": "uploaded",
            "analyzed_at": None,
            "document_date": None,
            "diagnosis": None,
            "drugs": [],
            "raw_text": None,
            "ocr_raw": None,
            "file_path": file_path,  # ✅ start_analysis에서 쓰게 됨
        }
        return {"scan_id": scan_id, "status": "uploaded"}

    async def start_analysis(self, user, scan_id: int) -> dict:
        cur = await self.get_result(user, scan_id)

        file_path = cur.get("file_path")
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업로드된 파일 경로(file_path)가 없습니다.",
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

        # ✅ 체크리스트 seed(임시 서비스 유지)
        await self.med_service.ensure_day_seed(user_id=user.id, date=doc_date)
        await self.health_service.ensure_day_seed(user_id=user.id, date=doc_date)

        diagnosis = cur.get("diagnosis")
        drug_names: list[str] = cur.get("drugs") or []

        disease_obj = None
        if diagnosis:
            disease_obj = await Disease.get_or_none(name=diagnosis)
            if not disease_obj:
                # 선택: disease 자동 생성할지 정책 결정
                disease_obj = await Disease.create(name=diagnosis)

        created_prescriptions: list[int] = []

        start = parse_date_yyyy_mm_dd(doc_date)
        end = start  # MVP: 하루짜리

        for drug_name in drug_names:
            drug_obj = await Drug.get_or_none(name=drug_name)
            if not drug_obj:
                drug_obj = await Drug.create(name=drug_name)

            prescription = await Prescription.create(
                user=user,
                disease=disease_obj,
                drug=drug_obj,
                start_date=start,
                end_date=end,
                dose_count=1,
                dose_amount="1",
                dose_unit="정",
            )
            created_prescriptions.append(prescription.id)

        cur["status"] = "saved"

        return {
            "scan_id": scan_id,
            "saved": True,
            "seeded_date": doc_date,
            "created_prescriptions": created_prescriptions,
        }
