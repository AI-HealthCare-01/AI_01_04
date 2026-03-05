from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, UploadFile
from starlette import status

from app.core import config
from app.dtos.scan import ScanResultUpdateRequest
from app.integrations.ocr.exceptions import (
    OCRAuthError,
    OCRBadRequestError,
    OCRConfigError,
    OCRError,
    OCRRateLimitError,
    OCRServerError,
    OCRTimeoutError,
)
from app.integrations.ocr.naver_ocr_client import NaverOCRClient
from app.integrations.ocr.openai_client import ai_postprocess
from app.integrations.ocr.parser import parse_ocr_result
from app.models.diseases import Disease
from app.models.drugs import Drug
from app.models.prescriptions import Prescription
from app.repositories.scan_repository import ScanRepository
from app.services.health import HealthService
from app.services.medication import MedicationService
from app.services.recommendations import RecommendationService
from app.utils.datetime import parse_date_yyyy_mm_dd
from app.utils.files import save_user_upload_file

logger = logging.getLogger(__name__)


class ScanAnalysisService:
    def __init__(self):
        self.scan_repo = ScanRepository()
        self.med_service = MedicationService()
        self.health_service = HealthService()
        self.ocr_client = NaverOCRClient()
        self.recommendation_service = RecommendationService()

    async def upload_file(self, user, file: UploadFile) -> dict:
        try:
            base_dir = getattr(config, "FILE_STORAGE_DIR", "./artifacts")
            file_path = await save_user_upload_file(user_id=user.id, upload=file, base_dir=base_dir)
            scan_data = await self.scan_repo.create(user_id=user.id, file_path=file_path)
            return {"scan_id": scan_data["scan_id"], "status": "uploaded"}
        except Exception as e:
            logger.exception("upload_file failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def _handle_ocr_analysis(self, user_id: int, scan_id: int, file_path: str) -> tuple[dict, dict]:
        """OCR 분석 및 에러 처리"""
        try:
            raw = await self.ocr_client.analyze_file(file_path=file_path)
            parsed = parse_ocr_result(raw)
            # OCR 호출은 성공했지만 텍스트를 못 읽은 경우를 명확히 구분한다.
            if not parsed.get("raw_text"):
                await self.scan_repo.update(user_id, scan_id, status="failed")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="OCR 텍스트 추출에 실패했습니다. 더 선명한 이미지로 다시 시도해주세요.",
                )
            return raw, parsed
        except HTTPException:
            raise
        except OCRConfigError as e:
            await self.scan_repo.update(user_id, scan_id, status="failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OCR 설정이 올바르지 않습니다. 관리자에게 문의해주세요.",
            ) from e
        except OCRTimeoutError as e:
            await self.scan_repo.update(user_id, scan_id, status="failed")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="OCR 처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
            ) from e
        except OCRRateLimitError as e:
            await self.scan_repo.update(user_id, scan_id, status="failed")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="OCR 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
            ) from e
        except OCRAuthError as e:
            await self.scan_repo.update(user_id, scan_id, status="failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OCR 인증에 실패했습니다. 관리자에게 문의해주세요.",
            ) from e
        except OCRBadRequestError as e:
            await self.scan_repo.update(user_id, scan_id, status="failed")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OCR 요청 형식이 올바르지 않습니다. 파일 형식/크기를 확인해주세요.",
            ) from e
        except OCRServerError as e:
            await self.scan_repo.update(user_id, scan_id, status="failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OCR 서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            ) from e
        except OCRError as e:
            await self.scan_repo.update(user_id, scan_id, status="failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OCR 처리 중 오류가 발생했습니다.",
            ) from e

    async def _handle_ai_postprocess(self, user_id: int, scan_id: int, parsed: dict, raw: dict) -> dict:
        """AI 후처리 및 에러 처리"""
        try:
            ai_result = ai_postprocess(raw_text=parsed.get("raw_text") or "", ocr_raw=raw)
            if not isinstance(ai_result, dict):
                raise ValueError("invalid AI response type")
            return ai_result
        except Exception as e:
            await self.scan_repo.update(user_id, scan_id, status="failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 후처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            ) from e

    async def start_analysis(self, user, scan_id: int) -> dict:
        try:
            cur = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
            if not cur:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")

            file_path = cur.get("file_path")
            if not file_path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="업로드된 파일 경로(file_path)가 없습니다.",
                )

            await self.scan_repo.update(user.id, scan_id, status="processing")

            raw, parsed = await self._handle_ocr_analysis(user.id, scan_id, file_path)
            ai_result = await self._handle_ai_postprocess(user.id, scan_id, parsed, raw)

            await self.scan_repo.update(
                user.id,
                scan_id,
                status="done",
                analyzed_at=datetime.now().isoformat(),
                document_date=ai_result.get("document_date"),
                diagnosis=ai_result.get("diagnosis"),
                drugs=ai_result.get("drugs", []),
                raw_text=ai_result.get("raw_text"),
                ocr_raw=ai_result.get("ocr_raw"),
            )

            return {"scan_id": scan_id, "status": "done"}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("start_analysis failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_result(self, user, scan_id: int) -> dict:
        scan = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")
        return scan

    async def update_result(self, user, scan_id: int, data: ScanResultUpdateRequest) -> dict:
        try:
            cur = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
            if not cur:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")

            update_fields: dict[str, Any] = {}
            if data.document_date is not None:
                parse_date_yyyy_mm_dd(data.document_date)
                update_fields["document_date"] = data.document_date
            if data.diagnosis is not None:
                update_fields["diagnosis"] = data.diagnosis
            if data.drugs is not None:
                update_fields["drugs"] = data.drugs

            if update_fields:
                update_fields["status"] = "updated"
                await self.scan_repo.update(user.id, scan_id, **update_fields)

            return await self.scan_repo.get_by_id_for_user(user.id, scan_id)  # type: ignore
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("update_result failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def save_result(self, user, scan_id: int) -> dict:
        try:
            cur = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
            if not cur:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")

            doc_date = cur.get("document_date")
            if not doc_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="처방/진단 날짜(document_date)가 필요합니다. 결과 화면에서 입력/수정 후 저장해주세요.",
                )

            await self.med_service.ensure_day_seed(user_id=user.id, date=doc_date)
            await self.health_service.ensure_day_seed(user_id=user.id, date=doc_date)

            diagnosis = cur.get("diagnosis")
            drug_names_raw: Any = cur.get("drugs", [])
            drug_names: list[str] = drug_names_raw if isinstance(drug_names_raw, list) else []

            disease_obj = None
            if diagnosis:
                disease_obj, _ = await Disease.get_or_create(name=diagnosis)

            created_prescriptions: list[int] = []
            skipped_duplicates: list[str] = []
            start = parse_date_yyyy_mm_dd(doc_date)
            end = start

            for drug_name in drug_names:
                drug_obj, _ = await Drug.get_or_create(name=drug_name)

                # 중복 방지: 같은 사용자/약/기간(+질병) 처방은 생성하지 않음
                exists_qs = Prescription.filter(
                    user_id=user.id,
                    drug_id=drug_obj.id,
                    start_date=start,
                    end_date=end,
                )
                if disease_obj is not None:
                    exists_qs = exists_qs.filter(disease_id=disease_obj.id)
                else:
                    exists_qs = exists_qs.filter(disease_id__isnull=True)

                already = await exists_qs.first()
                if already:
                    skipped_duplicates.append(drug_name)
                    continue

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

            await self.scan_repo.update(user.id, scan_id, status="saved")

            try:
                await self.recommendation_service.get_for_scan(user_id=user.id, scan_id=scan_id)
            except Exception:
                logger.exception("recommendation generation failed (ignored)")

            return {
                "scan_id": scan_id,
                "saved": True,
                "seeded_date": doc_date,
                "created_prescriptions": created_prescriptions,
                "skipped_duplicates": skipped_duplicates,
                "created_count": len(created_prescriptions),
                "skipped_count": len(skipped_duplicates),
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("save_result failed")
            raise HTTPException(status_code=500, detail=str(e)) from e
