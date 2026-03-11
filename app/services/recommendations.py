from __future__ import annotations

import logging
import re
from typing import Any, cast

from fastapi import HTTPException
from starlette import status

from app.dtos.recommendations import RecommendationType, RecommendationUpdateRequest
from app.repositories.disease_repository import DiseaseRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.scan_repository import ScanRepository
from app.repositories.vector_document_repository import VectorDocumentRepository
from app.services.embedding import encode

logger = logging.getLogger(__name__)


def _normalize_rec_type(raw: Any) -> RecommendationType:
    """
    recommendation_type 값을 API 응답용 표준 타입으로 정규화한다.

    Args:
        raw (Any):
            원본 recommendation_type 값

    Returns:
        RecommendationType:
            정규화된 추천 타입
    """
    s = str(raw or "").strip().lower()

    exact_map = {
        "lifestyle": "lifestyle",
        "general_care": "lifestyle",
        "daily_care": "lifestyle",
        "self_care": "lifestyle",
        "medication": "medication",
        "medication_caution": "warning",
        "drug_caution": "warning",
        "warning": "warning",
        "caution": "warning",
        "followup": "followup",
        "follow_up": "followup",
        "follow-up": "followup",
        "monitoring": "followup",
    }

    if s in exact_map:
        return cast(RecommendationType, exact_map[s])

    if "medication" in s and "caution" in s:
        return "warning"
    if "drug" in s and "caution" in s:
        return "warning"
    if "warn" in s or "caution" in s:
        return "warning"
    if "follow" in s or "monitor" in s:
        return "followup"
    if "drug" in s or "medicine" in s or "medication" in s:
        return "medication"
    return "lifestyle"


def _rec_to_response_dict(rec: Any) -> dict:
    """
    Recommendation ORM 객체를 API 응답용 dict로 변환한다.

    Args:
        rec (Any):
            Recommendation ORM 객체

    Returns:
        dict:
            API 응답용 추천 데이터
    """
    return {
        "id": rec.id,
        "recommendation_type": _normalize_rec_type(getattr(rec, "recommendation_type", None)),
        "content": rec.content,
        "score": getattr(rec, "score", None),
        "is_selected": bool(getattr(rec, "is_selected", False)),
        "rank": getattr(rec, "rank", None),
    }


class RecommendationService:
    def __init__(self):
        self.recommendation_repo = RecommendationRepository()
        self.scan_repo = ScanRepository()
        self.vector_doc_repo = VectorDocumentRepository()
        self.disease_repo = DiseaseRepository()

    def _normalize_document_type(self, raw: Any) -> str:
        """
        문서 유형 값을 정규화한다.

        Args:
            raw (Any):
                원본 document_type 값

        Returns:
            str:
                정규화된 document_type
        """
        value = str(raw or "prescription").strip().lower()
        if value in {"prescription", "medical_record"}:
            return value
        return "prescription"

    def _looks_like_disease_code(self, value: str | None) -> bool:
        """
        문자열이 질병분류코드(KCD/ICD) 형태인지 대략 판별한다.

        예:
            B15, I10, J00, E119, M545

        Args:
            value (str | None):
                diagnosis 후보 문자열

        Returns:
            bool:
                질병코드 형태로 보이면 True
        """
        if not value:
            return False

        text = value.strip().upper()
        return bool(re.fullmatch(r"[A-Z]\d{2,4}", text))

    def _build_vector_query(
        self,
        *,
        diagnosis: str | None,
        disease_name: str | None,
        drugs: list[str],
        clinical_note: str | None = None,
    ) -> str:
        """
        벡터 검색용 질의 문자열을 생성한다.

        Args:
            diagnosis (str | None):
                스캔에서 추출된 진단명 또는 질병코드
            disease_name (str | None):
                매칭된 질환명
            drugs (list[str]):
                약물명 목록
            clinical_note (str | None):
                진료기록 요약 텍스트

        Returns:
            str:
                임베딩 검색에 사용할 질의 문자열
        """
        parts: list[str] = []

        if disease_name:
            parts.append(disease_name)

        if diagnosis and diagnosis != disease_name:
            parts.append(diagnosis)

        if clinical_note:
            parts.append(clinical_note)

        if drugs:
            parts.extend(drugs[:5])

        return " ".join(part for part in parts if part).strip()

    async def _match_disease(self, diagnosis: str | None) -> Any | None:
        """
        diagnosis 값을 기반으로 질환을 매칭한다.

        매칭 우선순위:
        1. 질병코드 형태면 icd_code 매칭
        2. 질환명 정확 일치
        3. 질환명 부분 일치

        Args:
            diagnosis (str | None):
                스캔 결과에서 저장된 diagnosis 값
                (질환명 또는 질병코드일 수 있음)

        Returns:
            Any | None:
                매칭된 Disease 객체
        """
        if not diagnosis:
            return None

        value = diagnosis.strip()
        if not value:
            return None

        if self._looks_like_disease_code(value):
            disease = await self.disease_repo.get_by_icd_code(value.upper())
            if disease:
                return disease

        disease = await self.disease_repo.get_by_name(value)
        if disease:
            return disease

        diseases = await self.disease_repo.list_by_name_contains(value, limit=1)
        if diseases:
            return diseases[0]

        return None

    async def _create_recommendation(
        self,
        *,
        user_id: int,
        batch_id: int,
        scan_id: int,
        recommendation_type: str,
        source: str,
        content: str,
        score: float,
        rank: int,
        status_value: str = "active",
    ) -> Any | None:
        """
        Recommendation 레코드 1건을 생성한다.

        Args:
            user_id (int):
                사용자 ID
            batch_id (int):
                RecommendationBatch ID
            scan_id (int):
                스캔 ID
            recommendation_type (str):
                추천 유형
            source (str):
                추천 생성 출처
            content (str):
                추천 문구
            score (float):
                추천 점수
            rank (int):
                정렬 순위
            status_value (str):
                추천 상태값

        Returns:
            Any | None:
                생성된 Recommendation 객체
        """
        return await self.recommendation_repo.create_recommendation(
            user_id=user_id,
            batch_id=batch_id,
            scan_id=scan_id,
            recommendation_type=recommendation_type,
            source=source,
            content=content,
            score=score,
            rank=rank,
            status=status_value,
        )

    async def _build_guideline_recommendations(
        self,
        *,
        user_id: int,
        scan_id: int,
        batch_id: int,
        diagnosis: str | None,
    ) -> list[Any]:
        """
        diagnosis를 질환에 매칭한 뒤 DiseaseGuideline 기반 추천을 생성한다.

        Args:
            user_id (int):
                사용자 ID
            scan_id (int):
                스캔 ID
            batch_id (int):
                RecommendationBatch ID
            diagnosis (str | None):
                진단명 또는 질병코드

        Returns:
            list[Any]:
                생성된 Recommendation 객체 목록
        """
        created: list[Any] = []

        disease = await self._match_disease(diagnosis)
        if not disease:
            return created

        guidelines = await self.disease_repo.get_guidelines_by_disease(disease.id)
        if not guidelines:
            return created

        for idx, guideline in enumerate(guidelines, start=1):
            rec = await self._create_recommendation(
                user_id=user_id,
                batch_id=batch_id,
                scan_id=scan_id,
                recommendation_type=guideline.category,
                source="disease_guideline_seed",
                content=guideline.content,
                score=0.95,
                rank=idx,
                status_value="candidate",
            )
            if rec:
                created.append(rec)

        return created

    async def _build_prescription_recommendations(
        self,
        *,
        user_id: int,
        scan_id: int,
        batch_id: int,
        diagnosis: str | None,
        drugs: list[str],
    ) -> list[Any]:
        """
        처방전 스캔 결과를 기반으로 추천을 생성한다.

        우선순위:
        1. 질환 guideline 기반 추천
        2. 없으면 vector 검색 또는 기본 문구
        3. 약물명 기반 복약 안내 추천

        Args:
            user_id (int):
                사용자 ID
            scan_id (int):
                스캔 ID
            batch_id (int):
                추천 배치 ID
            diagnosis (str | None):
                진단명 또는 질병코드
            drugs (list[str]):
                스캔에서 추출된 약물명 목록

        Returns:
            list[Any]:
                생성된 Recommendation 객체 목록
        """
        created: list[Any] = []

        guideline_recs = await self._build_guideline_recommendations(
            user_id=user_id,
            scan_id=scan_id,
            batch_id=batch_id,
            diagnosis=diagnosis,
        )
        created.extend(guideline_recs)

        if not created and diagnosis:
            matched_disease = await self._match_disease(diagnosis)
            disease_name = matched_disease.name if matched_disease else None

            query = self._build_vector_query(
                diagnosis=diagnosis,
                disease_name=disease_name,
                drugs=drugs,
            )

            similar_docs: list[Any] = []
            if query:
                vector = encode(query)
                similar_docs = await self.vector_doc_repo.search_similar(
                    vector,
                    reference_type="disease_guideline",
                    top_k=3,
                )

            if similar_docs:
                for i, doc in enumerate(similar_docs, start=1):
                    rec = await self._create_recommendation(
                        user_id=user_id,
                        batch_id=batch_id,
                        scan_id=scan_id,
                        recommendation_type="followup",
                        source="vector.disease_guideline",
                        content=doc.content,
                        score=0.9,
                        rank=100 + i,
                    )
                    if rec:
                        created.append(rec)
            else:
                rec = await self._create_recommendation(
                    user_id=user_id,
                    batch_id=batch_id,
                    scan_id=scan_id,
                    recommendation_type="followup",
                    source="scan.diagnosis",
                    content=f"진단 정보 '{diagnosis}' 기준으로 생활관리 및 추적 관찰 항목을 확인해보세요.",
                    score=0.6,
                    rank=150,
                )
                if rec:
                    created.append(rec)

        for i, drug in enumerate(drugs[:10], start=1):
            rec = await self._create_recommendation(
                user_id=user_id,
                batch_id=batch_id,
                scan_id=scan_id,
                recommendation_type="medication",
                source="scan.drugs",
                content=f"약물 '{drug}' 복용 관련 주의사항과 복용법을 확인해보세요.",
                score=0.7,
                rank=200 + i,
            )
            if rec:
                created.append(rec)

        return created

    async def _build_medical_record_recommendations(
        self,
        *,
        user_id: int,
        scan_id: int,
        batch_id: int,
        diagnosis: str | None,
        clinical_note: str | None,
    ) -> list[Any]:
        """
        진료기록지 스캔 결과를 기반으로 추천을 생성한다.

        우선순위:
        1. 질환 guideline 기반 추천
        2. 진료기록 임시 문구 기반 추천

        Args:
            user_id (int):
                사용자 ID
            scan_id (int):
                스캔 ID
            batch_id (int):
                추천 배치 ID
            diagnosis (str | None):
                진단명 또는 질병코드
            clinical_note (str | None):
                진료기록지에서 추출한 진료 내용

        Returns:
            list[Any]:
                생성된 Recommendation 객체 목록
        """
        created: list[Any] = []

        guideline_recs = await self._build_guideline_recommendations(
            user_id=user_id,
            scan_id=scan_id,
            batch_id=batch_id,
            diagnosis=diagnosis,
        )
        created.extend(guideline_recs)

        if diagnosis and not guideline_recs:
            rec = await self._create_recommendation(
                user_id=user_id,
                batch_id=batch_id,
                scan_id=scan_id,
                recommendation_type="followup",
                source="scan.medical_record.diagnosis",
                content=f"진단 정보 '{diagnosis}' 기준으로 증상 변화와 경과를 관찰하고 필요한 추적 진료 일정을 확인해보세요.",
                score=0.9,
                rank=100,
            )
            if rec:
                created.append(rec)

        if clinical_note:
            rec = await self._create_recommendation(
                user_id=user_id,
                batch_id=batch_id,
                scan_id=scan_id,
                recommendation_type="lifestyle",
                source="scan.medical_record.clinical_note",
                content="진료기록지에 기재된 진료 내용과 생활지도에 맞춰 일상 관리 항목을 꾸준히 실천해보세요.",
                score=0.75,
                rank=200,
            )
            if rec:
                created.append(rec)

            rec = await self._create_recommendation(
                user_id=user_id,
                batch_id=batch_id,
                scan_id=scan_id,
                recommendation_type="warning",
                source="scan.medical_record.clinical_note",
                content="진료기록지의 증상 및 소견 내용을 바탕으로 악화 징후가 있는지 주의 깊게 관찰해보세요.",
                score=0.7,
                rank=201,
            )
            if rec:
                created.append(rec)

        return created

    async def _build_fallback_recommendation(
        self,
        *,
        user_id: int,
        scan_id: int,
        batch_id: int,
        document_type: str,
    ) -> list[Any]:
        """
        질환/약물/진료내용 기반 추천 생성이 어려울 때 기본 추천 1건을 생성한다.

        Args:
            user_id (int):
                사용자 ID
            scan_id (int):
                스캔 ID
            batch_id (int):
                추천 배치 ID
            document_type (str):
                문서 유형

        Returns:
            list[Any]:
                생성된 Recommendation 객체 목록
        """
        if document_type == "medical_record":
            content = (
                "진료기록지에서 진단명이나 핵심 진료 내용을 충분히 추출하지 못했어요. "
                "증상 기록을 정리하고 기본적인 건강관리 가이드를 먼저 확인해보세요."
            )
            source = "scan.medical_record"
        else:
            content = "스캔 결과에서 진단/약물 정보를 찾지 못했어요. 텍스트 보정 또는 수동 입력 후 다시 시도해 주세요."
            source = "scan"

        rec = await self._create_recommendation(
            user_id=user_id,
            batch_id=batch_id,
            scan_id=scan_id,
            recommendation_type="lifestyle",
            source=source,
            content=content,
            score=0.1,
            rank=999,
        )
        return [rec] if rec else []

    async def get_for_scan(self, user_id: int, scan_id: int) -> dict:
        """
        scan 기반 추천을 조회하거나 새로 생성한다.

        처리 흐름:
        1. scan 조회
        2. 기존 추천 존재 여부 확인
        3. 문서 유형별 추천 생성
        4. 생성 결과 반환

        Args:
            user_id (int):
                사용자 ID
            scan_id (int):
                스캔 ID

        Returns:
            dict:
                scan_id와 추천 목록을 포함한 응답 데이터
        """
        scan = await self.scan_repo.get_by_id_for_user(user_id, scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found")

        existing = await self.recommendation_repo.list_by_user_scan(user_id=user_id, scan_id=scan_id)
        if existing:
            return {"scan_id": scan_id, "items": [_rec_to_response_dict(r) for r in existing]}

        document_type = self._normalize_document_type(scan.get("document_type"))
        diagnosis_raw = scan.get("diagnosis")
        diagnosis = diagnosis_raw.strip() if isinstance(diagnosis_raw, str) and diagnosis_raw.strip() else None

        clinical_note_raw = scan.get("clinical_note")
        clinical_note = clinical_note_raw if isinstance(clinical_note_raw, str) and clinical_note_raw.strip() else None

        drugs_raw = scan.get("drugs") or []
        drugs: list[str] = drugs_raw if isinstance(drugs_raw, list) else []

        batch = await self.recommendation_repo.create_batch(
            user_id=user_id,
            retrieval_strategy=f"scan-{document_type}-mvp",
        )

        created: list[Any] = []

        if document_type == "medical_record":
            created.extend(
                await self._build_medical_record_recommendations(
                    user_id=user_id,
                    scan_id=scan_id,
                    batch_id=batch.id,
                    diagnosis=diagnosis,
                    clinical_note=clinical_note,
                )
            )
        else:
            created.extend(
                await self._build_prescription_recommendations(
                    user_id=user_id,
                    scan_id=scan_id,
                    batch_id=batch.id,
                    diagnosis=diagnosis,
                    drugs=drugs,
                )
            )

        if not created:
            created.extend(
                await self._build_fallback_recommendation(
                    user_id=user_id,
                    scan_id=scan_id,
                    batch_id=batch.id,
                    document_type=document_type,
                )
            )

        return {"scan_id": scan_id, "items": [_rec_to_response_dict(r) for r in created]}

    async def list_by_user(self, user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        사용자의 추천 목록을 조회한다.

        Args:
            user_id (int):
                사용자 ID
            limit (int):
                조회 개수 제한
            offset (int):
                조회 시작 위치

        Returns:
            list[dict]:
                추천 목록
        """
        try:
            recs = await self.recommendation_repo.list_by_user(user_id, limit=limit, offset=offset)
            return [_rec_to_response_dict(r) for r in recs]
        except Exception as e:
            logger.exception("list_by_user failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def list_active(self, user_id: int) -> list[dict]:
        """
        현재 활성 상태인 추천 목록을 조회한다.

        Args:
            user_id (int):
                사용자 ID

        Returns:
            list[dict]:
                활성 추천 목록
        """
        try:
            active_recs = await self.recommendation_repo.list_active_for_user(user_id)
            return [_rec_to_response_dict(ar.recommendation) for ar in active_recs]
        except Exception as e:
            logger.exception("list_active failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def update(self, user_id: int, recommendation_id: int, data: RecommendationUpdateRequest) -> dict:
        """
        추천 내용을 수정하거나 선택 여부를 갱신한다.

        Args:
            user_id (int):
                사용자 ID
            recommendation_id (int):
                추천 ID
            data (RecommendationUpdateRequest):
                수정 요청 데이터

        Returns:
            dict:
                수정된 추천 데이터
        """
        try:
            rec = await self.recommendation_repo.get_recommendation_for_user(user_id, recommendation_id)
            if not rec:
                raise HTTPException(status_code=404, detail="Recommendation not found")

            update_fields: list[str] = []
            if data.content is not None:
                rec.content = data.content
                update_fields.append("content")
            if data.is_selected is not None:
                rec.is_selected = data.is_selected
                update_fields.append("is_selected")

            if update_fields:
                await rec.save(update_fields=update_fields)

            return _rec_to_response_dict(rec)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("update failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def delete(self, user_id: int, recommendation_id: int) -> None:
        """
        추천을 삭제 상태로 변경한다.

        Args:
            user_id (int):
                사용자 ID
            recommendation_id (int):
                추천 ID
        """
        try:
            rec = await self.recommendation_repo.get_recommendation_for_user(user_id, recommendation_id)
            if not rec:
                raise HTTPException(status_code=404, detail="Recommendation not found")

            rec.status = "revoked"
            await rec.save(update_fields=["status"])
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("delete failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def save_for_scan(self, user_id: int, scan_id: int) -> dict:
        """
        scan 기반 추천을 active 추천으로 반영한다.

        처리 규칙:
        - scan_id로 생성된 추천이 없으면 먼저 생성한다.
        - is_selected=True 인 추천이 있으면 그것만 반영한다.
        - 선택된 추천이 없으면 전체 추천을 active로 반영한다.

        Args:
            user_id (int):
                사용자 ID
            scan_id (int):
                스캔 ID

        Returns:
            dict:
                저장 결과
        """
        try:
            recs = await self.recommendation_repo.list_by_user_scan(user_id=user_id, scan_id=scan_id)

            if not recs:
                generated = await self.get_for_scan(user_id=user_id, scan_id=scan_id)
                target_ids = [it["id"] for it in (generated.get("items") or [])]
            else:
                selected = [r.id for r in recs if r.is_selected is True]
                all_ids = [r.id for r in recs]
                target_ids = selected or all_ids

            await self.recommendation_repo.clear_active_for_user(user_id)
            await self.recommendation_repo.assign_active_many(user_id=user_id, recommendation_ids=target_ids)

            return {"scan_id": scan_id, "saved": True, "saved_count": len(target_ids)}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("save_for_scan failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def add_feedback(self, user_id: int, recommendation_id: int, feedback_type: str) -> dict:
        """
        추천 피드백을 저장한다.

        Args:
            user_id (int):
                사용자 ID
            recommendation_id (int):
                추천 ID
            feedback_type (str):
                피드백 유형

        Returns:
            dict:
                저장된 피드백 정보
        """
        try:
            fb = await self.recommendation_repo.add_feedback(user_id, recommendation_id, feedback_type=feedback_type)
            if not fb:
                raise HTTPException(status_code=404, detail="Recommendation not found")

            return {
                "recommendation_id": recommendation_id,
                "feedback_type": feedback_type,
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("add_feedback failed")
            raise HTTPException(status_code=500, detail=str(e)) from e
