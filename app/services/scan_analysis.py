"""스캔 분석 서비스.

파일 업로드, OCR 분석, AI 후처리, 처방전/진료기록지 저장을 담당한다.
document_type에 따라 prescription(처방전)과 medical_record(진료기록지)를 분기 처리한다.
상태 흐름: uploaded → processing → done → updated → saved / failed.
"""

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

    def _normalize_document_type(self, document_type: str | None) -> str:
        """입력값을 prescription 또는 medical_record로 정규화한다.

        Args:
            document_type (str | None): 정규화할 문서 유형 문자열.

        Returns:
            str: 정규화된 문서 유형 (prescription 또는 medical_record).

        Raises:
            HTTPException: 허용되지 않는 문서 유형 시 400.
        """
        value = (document_type or "prescription").strip().lower()
        if value not in {"prescription", "medical_record"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="document_type must be one of: prescription, medical_record",
            )
        return value

    async def upload_file(
        self,
        user,
        file: UploadFile,
        document_type: str = "prescription",
    ) -> dict:
        """의료문서 파일을 업로드한다.

        확장자/용량 검증 후 저장하며, uploaded 상태로 스캔 레코드를 생성한다.

        Args:
            user: 업로드할 User 객체.
            file (UploadFile): 업로드할 의료문서 파일.
            document_type (str): 문서 유형 (prescription 또는 medical_record). 기본값 prescription.

        Returns:
            dict: scan_id, status, document_type가 담긴 딕셔너리.

        Raises:
            HTTPException: 허용되지 않는 문서 유형(400), 파일 처리 실패(500) 시.
        """
        try:
            normalized_document_type = self._normalize_document_type(document_type)  # [ADD]

            base_dir = getattr(config, "FILE_STORAGE_DIR", "./artifacts")
            file_path = await save_user_upload_file(user_id=user.id, upload=file, base_dir=base_dir)
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

    async def _handle_ocr_analysis(self, user_id: int, scan_id: int, file_path: str) -> tuple[dict, dict]:
        """OCR 분석을 실행하고 예외를 HTTPException으로 변환한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            scan_id (int): 분석할 스캔 ID.
            file_path (str): 분석할 파일 경로.

        Returns:
            tuple[dict, dict]: (OCR 원본 응답, 파싱된 결과) 튜플.

        Raises:
            HTTPException: OCR 텍스트 추출 실패(422), 설정 오류(500), 타임아웃(504),
                           요청 한도 초과(429), 인증 실패(500), 잘못된 요청(400), 서버 오류(502) 시.
        """
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

    async def _handle_ai_postprocess(
        self,
        user_id: int,
        scan_id: int,
        parsed: dict,
        raw: dict,
        document_type: str,
    ) -> dict:
        """AI 후처리를 실행하고 예외를 HTTPException으로 변환한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            scan_id (int): 처리할 스캔 ID.
            parsed (dict): OCR 파싱 결과.
            raw (dict): OCR 원본 응답.
            document_type (str): 문서 유형 (prescription 또는 medical_record).

        Returns:
            dict: AI 후처리 결과 (document_date, diagnosis, drugs 등).

        Raises:
            HTTPException: AI 후처리 실패 시 502.
        """
        try:
            # [CHANGED] 문서 유형에 따라 후처리 프롬프트/로직을 분기할 수 있도록 document_type 전달
            ai_result = ai_postprocess(
                raw_text=parsed.get("raw_text") or "",
                ocr_raw=raw,
                document_type=document_type,
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

    async def prepare_analysis(self, user, scan_id: int) -> dict:
        """백그라운드 분석 시작 전 상태를 processing으로 변경하고 즉시 반환"""
        cur = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
        if not cur:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")
        if not cur.get("file_path"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="업로드된 파일 경로(file_path)가 없습니다."
            )
        await self.scan_repo.update(user.id, scan_id, status="processing")
        return {"scan_id": scan_id, "status": "processing", "document_type": cur.get("document_type")}

    async def run_analysis_background(self, user, scan_id: int) -> None:
        """백그라운드에서 OCR 분석 실행"""
        try:
            cur = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
            if not cur:
                return
            document_type = self._normalize_document_type(cur.get("document_type"))
            raw, parsed = await self._handle_ocr_analysis(user.id, scan_id, cur["file_path"])
            ai_result = await self._handle_ai_postprocess(user.id, scan_id, parsed, raw, document_type=document_type)
            await self.scan_repo.update(
                user.id,
                scan_id,
                status="done",
                analyzed_at=datetime.now().isoformat(),
                document_type=document_type,
                document_date=ai_result.get("document_date"),
                diagnosis=ai_result.get("diagnosis"),
                clinical_note=ai_result.get("clinical_note"),
                drugs=ai_result.get("drugs", []),
                raw_text=ai_result.get("raw_text"),
                ocr_raw=ai_result.get("ocr_raw"),
            )
        except HTTPException:
            pass
        except Exception:
            logger.exception("run_analysis_background failed: scan_id=%s", scan_id)
            await self.scan_repo.update(user.id, scan_id, status="failed")

    async def start_analysis(self, user, scan_id: int) -> dict:
        """스캔에 대한 OCR 분석을 시작한다.

        OCR 호출 → AI 후처리 → 스캔 결과 저장 순서로 실행한다.
        실패 시 스캔 상태를 failed로 업데이트한다.

        Args:
            user: 요청한 User 객체.
            scan_id (int): 분석할 스캔 ID.

        Returns:
            dict: scan_id, status, document_type가 담긴 딕셔너리.

        Raises:
            HTTPException: 스캔 미존재(404), OCR 실패(400/429/500/502/504), AI 후처리 실패(502) 시.
        """
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

            document_type = self._normalize_document_type(cur.get("document_type"))  # [ADD]

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
                analyzed_at=datetime.now().isoformat(),
                document_type=document_type,
                document_date=ai_result.get("document_date"),
                diagnosis=ai_result.get("diagnosis"),
                clinical_note=ai_result.get("clinical_note"),
                drugs=ai_result.get("drugs", []),
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

    async def get_result(self, user, scan_id: int) -> dict:
        """스캔 결과를 조회한다.

        Args:
            user: 요청한 User 객체.
            scan_id (int): 조회할 스캔 ID.

        Returns:
            dict: 스캔 정보 딕셔너리.

        Raises:
            HTTPException: 스캔이 없거나 소유자가 다를 시 404.
        """
        scan = await self.scan_repo.get_by_id_for_user(user.id, scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found.")
        return scan

    async def update_result(self, user, scan_id: int, data: ScanResultUpdateRequest) -> dict:
        """스캔 결과를 수동으로 수정한다 (diagnosis, drugs, document_date 등).

        Args:
            user: 요청한 User 객체.
            scan_id (int): 수정할 스캔 ID.
            data (ScanResultUpdateRequest): 수정할 필드가 담긴 요청 데이터.

        Returns:
            dict: 업데이트된 스캔 정보 딕셔너리.

        Raises:
            HTTPException: 스캔 미존재(404), 날짜 형식 오류(400), 예기치 않은 오류(500) 시.
        """
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
            if data.clinical_note is not None:  # [ADD]
                update_fields["clinical_note"] = data.clinical_note
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

    async def _create_prescriptions(
        self, user, doc_date: str, diagnosis: str | None, drug_names: list[str]
    ) -> tuple[list[int], int, list[str]]:
        """처방전을 생성한다 (중복 방지 포함).

        Args:
            user: 소유자 User 객체.
            doc_date (str): 처방 날짜 (YYYY-MM-DD).
            diagnosis (str | None): 진단명. 없으면 None.
            drug_names (list[str]): 생성할 약품명 목록.

        Returns:
            tuple[list[int], int, list[str]]: (생성된 처방전 ID 목록, 스킵 건수, 스킵된 약품명 목록).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        disease_obj = None
        if diagnosis:
            disease_obj = await Disease.get_or_none(name=diagnosis)
            if not disease_obj:
                disease_obj = await Disease.create(name=diagnosis)

        created: list[int] = []
        skipped = 0
        skipped_duplicates: list[str] = []
        start = parse_date_yyyy_mm_dd(doc_date)
        end = start

        for drug_name in drug_names:
            drug_obj, _ = await Drug.get_or_create(name=drug_name)

            exists_qs = Prescription.filter(user_id=user.id, drug_id=drug_obj.id, start_date=start, end_date=end)
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

    async def save_result(self, user, scan_id: int) -> dict:
        """스캔 결과를 저장한다.

        - prescription: 처방전 생성 + 복약/건강관리 시드
        - medical_record: 건강관리 시드 + 추천 생성
        - 중복 처방전은 스킵하여 멱등성을 보장한다.

        Args:
            user: 요청한 User 객체.
            scan_id (int): 저장할 스캔 ID.

        Returns:
            dict: scan_id, saved, seeded_date, document_type, created_prescriptions,
                  skipped_count, skipped_duplicates가 담긴 딕셔너리.

        Raises:
            HTTPException: 스캔 미존재(404), document_date 누락(400), 예기치 않은 오류(500) 시.
        """
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
                    cur.get("diagnosis"),
                    drug_names,
                )

            else:  # medical_record
                # 진료기록지는 약 처방 생성 대신 건강관리/recommendation 중심으로 저장
                if doc_date:
                    await self.health_service.ensure_day_seed(user_id=user.id, date=doc_date)

                # TODO: disease_repository / user_features 연동 시
                # - diagnosis 또는 disease_code 기반 질환 매칭
                # - 추천 생성 시점의 feature snapshot 저장
                # 을 여기 또는 recommendation service에서 확장

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
                "skipped_count": skipped_count,
                "skipped_duplicates": skipped_duplicates,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("save_result failed")
            raise HTTPException(status_code=500, detail=str(e)) from e
