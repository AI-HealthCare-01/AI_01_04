"""스캔 분석 서비스.

파일 업로드, OCR 분석, AI 후처리, 처방전/진료기록지 저장을 담당한다.
document_type에 따라 prescription(처방전)과 medical_record(진료기록지)를 분기 처리한다.
상태 흐름: uploaded → processing → done → updated → saved / failed.
"""

from __future__ import annotations

import logging
import re
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
from app.models.diseases import Disease, DiseaseCodeMapping
from app.models.drugs import Drug
from app.models.prescriptions import Prescription
from app.repositories.scan_repository import ScanRepository
from app.repositories.vector_document_repository import VectorDocumentRepository
from app.services.embedding import encode
from app.services.health import HealthService
from app.services.medication import MedicationService
from app.services.recommendations import RecommendationService
from app.utils.datetime import DateTimeError, parse_date_yyyy_mm_dd
from app.utils.files import save_user_upload_file

logger = logging.getLogger(__name__)


class ScanAnalysisService:
    """스캔 업로드/분석/수정/저장을 담당하는 서비스."""

    def __init__(self) -> None:
        self.scan_repo = ScanRepository()
        self.med_service = MedicationService()
        self.health_service = HealthService()
        self.ocr_client = NaverOCRClient()
        self.recommendation_service = RecommendationService()
        self.vector_repo = VectorDocumentRepository()

    def _normalize_document_type(self, document_type: str | None) -> str:
        """입력값을 prescription 또는 medical_record로 정규화한다."""
        value = (document_type or "prescription").strip().lower()
        if value not in {"prescription", "medical_record"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="document_type must be one of: prescription, medical_record",
            )
        return value

    async def upload_file(
        self,
        user: Any,
        file: UploadFile,
        document_type: str = "prescription",
    ) -> dict[str, Any]:
        """의료문서 파일을 업로드하고 uploaded 상태의 scan 레코드를 생성한다."""
        try:
            normalized_document_type = self._normalize_document_type(document_type)

            base_dir = getattr(config, "FILE_STORAGE_DIR", "./artifacts")
            file_path = await save_user_upload_file(
                user_id=user.id,
                upload=file,
                base_dir=base_dir,
            )

            scan_data = await self.scan_repo.create(
                user_id=user.id,
                file_path=file_path,
                document_type=normalized_document_type,
            )

            return {
                "scan_id": scan_data["scan_id"],
                "status": "uploaded",
                "document_type": normalized_document_type,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("upload_file failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def _handle_ocr_analysis(
        self,
        user_id: int,
        scan_id: int,
        file_path: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """OCR 분석을 실행하고 예외를 HTTPException으로 변환한다."""
        try:
            raw = await self.ocr_client.analyze_file(file_path=file_path)
            parsed = parse_ocr_result(raw)

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

    async def _handle_ai_postprocess(
        self,
        user_id: int,
        scan_id: int,
        parsed: dict[str, Any],
        raw: dict[str, Any],
        document_type: str,
    ) -> dict[str, Any]:
        """AI 후처리를 실행하고 예외를 HTTPException으로 변환한다."""
        try:
            ai_result = await ai_postprocess(
                raw_text=parsed.get("raw_text") or "",
                ocr_raw=raw,
                document_type=document_type,
                parser_hints={
                    "candidate_dates": parsed.get("candidate_dates", []),
                    "candidate_diagnosis_codes": parsed.get("candidate_diagnosis_codes", []),
                    "candidate_drugs": parsed.get("candidate_drugs", []),
                },
            )
            if not isinstance(ai_result, dict):
                raise ValueError("invalid AI response type")
            return ai_result
        except Exception as e:
            logger.exception("AI postprocess failed: scan_id=%s", scan_id)
            await self.scan_repo.update(user_id, scan_id, status="failed")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI 후처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            ) from e

    async def prepare_analysis(self, user: Any, scan_id: int) -> dict[str, Any]:
        """백그라운드 분석 시작 전 상태를 processing으로 변경하고 즉시 반환한다."""
        cur = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
        if not cur:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")
        if not cur.get("file_path"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업로드된 파일 경로(file_path)가 없습니다.",
            )

        await self.scan_repo.update(user.id, scan_id, status="processing")
        return {
            "scan_id": scan_id,
            "status": "processing",
            "document_type": cur.get("document_type"),
        }

    async def run_analysis_background(self, user: Any, scan_id: int) -> None:
        """백그라운드에서 OCR 분석 및 AI 후처리를 실행한다."""
        try:
            cur = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
            if not cur:
                return

            document_type = self._normalize_document_type(cur.get("document_type"))
            raw, parsed = await self._handle_ocr_analysis(user.id, scan_id, cur["file_path"])
            ai_result = await self._handle_ai_postprocess(
                user.id,
                scan_id,
                parsed,
                raw,
                document_type=document_type,
            )

            await self.scan_repo.update(
                user.id,
                scan_id,
                status="done",
                analyzed_at=datetime.now(config.TIMEZONE).isoformat(),
                document_type=document_type,
                document_date=ai_result.get("document_date"),
                diagnosis_list=ai_result.get("diagnosis_list", []),
                clinical_note=ai_result.get("clinical_note"),
                drugs=ai_result.get("drugs", []),
                unrecognized_drugs=ai_result.get("unrecognized_drugs", []),
                raw_text=ai_result.get("raw_text"),
                ocr_raw=ai_result.get("ocr_raw"),
            )
        except HTTPException as e:
            logger.exception("run_analysis_background http error: scan_id=%s", scan_id)
            await self.scan_repo.update(user.id, scan_id, status="failed", error_message=e.detail)
        except Exception as e:
            logger.exception("run_analysis_background failed: scan_id=%s", scan_id)
            await self.scan_repo.update(user.id, scan_id, status="failed", error_message=str(e))

    async def start_analysis(self, user: Any, scan_id: int) -> dict[str, Any]:
        """스캔에 대한 OCR 분석과 AI 후처리를 즉시 실행한다."""
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

            document_type = self._normalize_document_type(cur.get("document_type"))
            await self.scan_repo.update(user.id, scan_id, status="processing")

            raw, parsed = await self._handle_ocr_analysis(user.id, scan_id, file_path)
            ai_result = await self._handle_ai_postprocess(
                user.id,
                scan_id,
                parsed,
                raw,
                document_type=document_type,
            )

            await self.scan_repo.update(
                user.id,
                scan_id,
                status="done",
                analyzed_at=datetime.now(config.TIMEZONE).isoformat(),
                document_type=document_type,
                document_date=ai_result.get("document_date"),
                diagnosis_list=ai_result.get("diagnosis_list", []),
                clinical_note=ai_result.get("clinical_note"),
                drugs=ai_result.get("drugs", []),
                unrecognized_drugs=ai_result.get("unrecognized_drugs", []),
                raw_text=ai_result.get("raw_text"),
                ocr_raw=ai_result.get("ocr_raw"),
            )

            return {
                "scan_id": scan_id,
                "status": "done",
                "document_type": document_type,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("start_analysis failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_result(self, user: Any, scan_id: int) -> dict[str, Any]:
        """스캔 결과를 조회한다."""
        scan = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")
        return scan

    def _build_update_fields(self, data: ScanResultUpdateRequest) -> dict[str, Any]:
        """ScanResultUpdateRequest에서 업데이트할 필드 딕셔너리를 생성한다."""
        update_fields: dict[str, Any] = {}
        if data.document_date is not None:
            parse_date_yyyy_mm_dd(data.document_date)
            update_fields["document_date"] = data.document_date
        if data.diagnosis is not None:
            update_fields["diagnosis_list"] = data.diagnosis if isinstance(data.diagnosis, list) else [data.diagnosis]
        if data.clinical_note is not None:
            update_fields["clinical_note"] = data.clinical_note
        if data.drugs is not None:
            update_fields["drugs"] = data.drugs
        return update_fields

    async def update_result(
        self,
        user: Any,
        scan_id: int,
        data: ScanResultUpdateRequest,
    ) -> dict[str, Any]:
        """스캔 결과를 수동으로 수정한다."""
        try:
            cur = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
            if not cur:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")

            update_fields = self._build_update_fields(data)
            if update_fields:
                update_fields["status"] = "updated"
                await self.scan_repo.update(user.id, scan_id, **update_fields)

            updated = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
            if not updated:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")
            return updated
        except HTTPException:
            raise
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except Exception as e:
            logger.exception("update_result failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def _resolve_disease(self, diag: str) -> Disease | None:
        """진단 문자열에서 Disease 객체를 조회하거나 생성한다."""
        diag_name = diag.strip()
        if not diag_name:
            return None
        m = re.match(r"^([A-Za-z]\d{2,5})\s+(.*)", diag_name)
        if m:
            kcd_code = m.group(1).upper()
            name = m.group(2).strip()
        else:
            kcd_code = diag_name.upper() if re.match(r"^[A-Za-z]\d{2,5}$", diag_name) else None
            if kcd_code:
                mapping = await DiseaseCodeMapping.get_or_none(code=kcd_code)
                name = mapping.name if mapping else kcd_code
            else:
                name = diag_name
        if kcd_code:
            disease_obj = await Disease.get_or_none(kcd_code=kcd_code)
        else:
            disease_obj = await Disease.get_or_none(name=name)
        return disease_obj or await Disease.create(name=name, kcd_code=kcd_code)

    async def _create_prescriptions(
        self,
        user: Any,
        doc_date: str,
        diagnosis_list: list[str],
        drug_names: list[str],
    ) -> tuple[list[int], int, list[str]]:
        """처방전 레코드를 생성한다.

        복수 진단을 지원하며, 각 진단-약물 조합에 대해 처방전을 생성한다.
        동일 사용자/동일 약물/동일 날짜/동일 질환 조합이 있으면 중복으로 간주하여 스킵한다.
        """
        disease_objects: list[Disease | None] = []
        for diag in diagnosis_list:
            disease_objects.append(await self._resolve_disease(diag))

        if not disease_objects:
            disease_objects = [None]

        created: list[int] = []
        skipped = 0
        skipped_duplicates: list[str] = []

        start = parse_date_yyyy_mm_dd(doc_date)
        end = start

        for drug_name_raw in drug_names:
            drug_name = drug_name_raw.strip()
            if not drug_name:
                continue

            query_vector = encode(drug_name)
            similar = await self.vector_repo.search_similar(
                query_vector,
                reference_type="drug",
                top_k=1,
            )
            _drug_similarity_threshold = 0.15
            if similar and getattr(similar[0], "_distance", 1.0) <= _drug_similarity_threshold:
                drug_obj = await Drug.get_or_none(id=similar[0].reference_id)
                if not drug_obj:
                    drug_obj, _ = await Drug.get_or_create(name=drug_name)
            else:
                drug_obj, _ = await Drug.get_or_create(name=drug_name)

            # 첫 번째 질환과만 처방전 연결 (1약물:1처방전)
            disease_obj = disease_objects[0]

            exists_qs = Prescription.filter(
                user_id=user.id,
                drug_id=drug_obj.id,
                start_date=start,
                end_date=end,
            )
            exists_qs = (
                exists_qs.filter(disease_id=disease_obj.id)
                if disease_obj
                else exists_qs.filter(disease_id__isnull=True)
            )

            if await exists_qs.first():
                skipped += 1
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
            created.append(prescription.id)

        return created, skipped, skipped_duplicates

    async def save_result(self, user: Any, scan_id: int) -> dict[str, Any]:
        """스캔 결과를 실제 서비스 데이터로 저장한다."""
        try:
            cur = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
            if not cur:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")

            document_type = self._normalize_document_type(cur.get("document_type"))
            doc_date = cur.get("document_date")

            created_prescriptions: list[int] = []
            skipped_count = 0
            skipped_duplicates: list[str] = []

            if document_type == "prescription":
                if not doc_date:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="처방/진단 날짜(document_date)가 필요합니다. 결과 화면에서 입력/수정 후 저장해주세요.",
                    )

                await self.med_service.ensure_day_seed(user_id=user.id, date=doc_date)
                await self.health_service.ensure_day_seed(user_id=user.id, date=doc_date)

                drug_names_raw: Any = cur.get("drugs", [])
                drug_names: list[str] = drug_names_raw if isinstance(drug_names_raw, list) else []

                created_prescriptions, skipped_count, skipped_duplicates = await self._create_prescriptions(
                    user,
                    doc_date,
                    cur.get("diagnosis_list", []),
                    drug_names,
                )

            else:
                if doc_date:
                    await self.health_service.ensure_day_seed(user_id=user.id, date=doc_date)

            await self.scan_repo.update(user.id, scan_id, status="saved")

            try:
                await self.recommendation_service.get_for_scan(user_id=user.id, scan_id=scan_id)
            except Exception:
                logger.exception("recommendation generation failed (ignored)")

            return {
                "scan_id": scan_id,
                "saved": True,
                "seeded_date": doc_date,
                "document_type": document_type,
                "created_prescriptions": created_prescriptions,
                "created_count": len(created_prescriptions),
                "skipped_count": skipped_count,
                "skipped_duplicates": skipped_duplicates,
            }
        except HTTPException:
            raise
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        except Exception as e:
            logger.exception("save_result failed")
            raise HTTPException(status_code=500, detail=str(e)) from e
