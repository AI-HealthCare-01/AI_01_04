from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import HTTPException
from starlette import status

from app.dtos.recommendations import RecommendationType, RecommendationUpdateRequest
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.scan_repository import ScanRepository
from app.repositories.vector_document_repository import VectorDocumentRepository
from app.services.embedding import encode

logger = logging.getLogger(__name__)


def _normalize_rec_type(raw: Any) -> RecommendationType:
    """
    raw 추천 타입 문자열을 RecommendationType으로 정규화.

    Args:
        raw (Any): 정규화할 원본 값.

    Returns:
        RecommendationType: 정규화된 추천 타입.
    """
    s = str(raw or "").lower()
    if s in {"lifestyle", "medication", "warning", "followup"}:
        return cast(RecommendationType, s)
    if "drug" in s or "medicine" in s:
        return "medication"
    if "warn" in s or "caution" in s:
        return "warning"
    if "follow" in s:
        return "followup"
    return "lifestyle"


def _rec_to_response_dict(rec: Any) -> dict:
    """
    Recommendation 인스턴스를 API 응답 딕셔너리로 변환.

    Args:
        rec (Any): Recommendation ORM 인스턴스.

    Returns:
        dict: id, recommendation_type, content, score, is_selected, rank 포함 딕셔너리.
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
    """
    추천 서비스.

    스캔 기반 추천 생성/조회/저장 및 피드백 관리를 담당.
    """

    def __init__(self):
        self.recommendation_repo = RecommendationRepository()
        self.scan_repo = ScanRepository()
        self.vector_doc_repo = VectorDocumentRepository()

    def _normalize_document_type(self, raw: Any) -> str:
        """
        문서 타입 문자열을 유효한 값으로 정규화.

        Args:
            raw (Any): 정규화할 원본 값.

        Returns:
            str: prescription 또는 medical_record.
        """
        value = str(raw or "prescription").strip().lower()
        if value in {"prescription", "medical_record"}:
            return value
        return "prescription"

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
        단일 추천 레코드 생성.

        Args:
            user_id (int): 사용자 ID.
            batch_id (int): 추천 배치 ID.
            scan_id (int): 스캔 ID.
            recommendation_type (str): 추천 타입.
            source (str): 추천 출처.
            content (str): 추천 콘텐츠.
            score (float): 추천 점수.
            rank (int): 순위.
            status_value (str): 상태값. 기본값 active.

        Returns:
            Any | None: 생성된 Recommendation 인스턴스 또는 None.
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
        처방전 기반 추천 목록 생성.

        Args:
            user_id (int): 사용자 ID.
            scan_id (int): 스캔 ID.
            batch_id (int): 추천 배치 ID.
            diagnosis (str | None): 진단명.
            drugs (list[str]): 약물명 목록.

        Returns:
            list[Any]: 생성된 Recommendation 인스턴스 목록.
        """
        created: list[Any] = []

        # TODO:
        # - disease_repository.py 연결 시 diagnosis -> 질환 매칭
        # - 매칭 성공 시 질환별 정교한 recommendation 문구/점수로 확장

        if diagnosis:
            query = (
                diagnosis + " " + " ".join(drugs[:5])
            )  # 진단명 + 약물명을 합쳐서 검색 쿼리 생성. 더 많은 정보를 담을수록 유사도 검색 품질이 올라감
            vector = encode(query)  # 텍스트를 1536차원 벡터로 변환
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
                        rank=i,
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
                    content=f"진단명 '{diagnosis}' 기준으로 생활관리 및 추적 관찰 항목을 확인해보세요",
                    score=0.9,
                    rank=1,
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
                rank=10 + i,
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
        진료기록지 기반 추천 목록 생성.

        Args:
            user_id (int): 사용자 ID.
            scan_id (int): 스캔 ID.
            batch_id (int): 추천 배치 ID.
            diagnosis (str | None): 진단명.
            clinical_note (str | None): 진료 내용.

        Returns:
            list[Any]: 생성된 Recommendation 인스턴스 목록.
        """
        created: list[Any] = []

        # TODO:
        # - disease_repository.py 연결 시 diagnosis / disease_code 기반 질환 매칭
        # - user_features snapshot 저장 로직 연결
        # - 진료기록지 내 symptom severity / symptom code 기반 rule 확장

        if diagnosis:
            rec = await self._create_recommendation(
                user_id=user_id,
                batch_id=batch_id,
                scan_id=scan_id,
                recommendation_type="followup",
                source="scan.medical_record.diagnosis",
                content=f"진단명 '{diagnosis}' 기준으로 증상 변화와 경과를 관찰하고 필요한 추적 진료 일정을 확인해보세요.",
                score=0.9,
                rank=1,
            )
            if rec:
                created.append(rec)

            rec = await self._create_recommendation(
                user_id=user_id,
                batch_id=batch_id,
                scan_id=scan_id,
                recommendation_type="lifestyle",
                source="scan.medical_record.diagnosis",
                content=f"진단명 '{diagnosis}' 관련 일반 건강관리 수칙과 생활습관 가이드를 확인해보세요.",
                score=0.8,
                rank=2,
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
                rank=10,
            )
            if rec:
                created.append(rec)

            rec = await self._create_recommendation(
                user_id=user_id,
                batch_id=batch_id,
                scan_id=scan_id,
                recommendation_type="warning",
                source="scan.medical_record.clinical_note",
                content="진료기록지의 증상/소견 내용을 바탕으로 악화 징후가 있는지 주의 깊게 관찰해보세요.",
                score=0.7,
                rank=11,
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
        추천 생성 실패 시 폴백 추천 생성.

        Args:
            user_id (int): 사용자 ID.
            scan_id (int): 스캔 ID.
            batch_id (int): 추천 배치 ID.
            document_type (str): 문서 타입.

        Returns:
            list[Any]: 폴백 Recommendation 인스턴스 목록.
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
        스캔 기반 추천 조회/생성.

        이미 생성된 추천이 있으면 재사용, 없으면 새로 생성.

        Args:
            user_id (int): 사용자 ID.
            scan_id (int): 스캔 ID.

        Returns:
            dict: scan_id와 items(추천 목록) 포함 딕셔너리.

        Raises:
            HTTPException: 스캔 미존재 시 404.
        """
        scan = await self.scan_repo.get_by_id_for_user(user_id, scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found")

        existing = await self.recommendation_repo.list_by_user_scan(user_id=user_id, scan_id=scan_id)
        if existing:
            return {"scan_id": scan_id, "items": [_rec_to_response_dict(r) for r in existing]}

        document_type = self._normalize_document_type(scan.get("document_type"))  # [ADD]
        diagnosis = scan.get("diagnosis")

        clinical_note_raw = scan.get("clinical_note")  # [ADD]
        clinical_note = (
            clinical_note_raw if isinstance(clinical_note_raw, str) and clinical_note_raw.strip() else None
        )  # [ADD]

        drugs_raw = scan.get("drugs") or []
        drugs: list[str] = drugs_raw if isinstance(drugs_raw, list) else []

        # TODO:
        # - user_features.py 연결 시 recommendation 생성 시점의 상태 snapshot 저장
        # - 질환/증상/복약/건강관리 이력을 함께 반영하는 확장 로직 추가

        batch = await self.recommendation_repo.create_batch(
            user_id=user_id,
            retrieval_strategy=f"scan-{document_type}-mvp",  # [CHANGED]
        )

        created: list[Any] = []

        if document_type == "medical_record":  # [ADD]
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
        사용자의 추천 목록 조회.

        Args:
            user_id (int): 사용자 ID.
            limit (int): 최대 반환 개수. 기본값 50.
            offset (int): 오프셋. 기본값 0.

        Returns:
            list[dict]: 추천 응답 딕셔너리 목록.

        Raises:
            HTTPException: 조회 실패 시 500.
        """
        try:
            recs = await self.recommendation_repo.list_by_user(user_id, limit=limit, offset=offset)
            return [_rec_to_response_dict(r) for r in recs]
        except Exception as e:
            logger.exception("list_by_user failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def list_active(self, user_id: int) -> list[dict]:
        """
        사용자의 활성 추천 목록 조회.

        Args:
            user_id (int): 사용자 ID.

        Returns:
            list[dict]: 활성 추천 응답 딕셔너리 목록.

        Raises:
            HTTPException: 조회 실패 시 500.
        """
        try:
            active_recs = await self.recommendation_repo.list_active_for_user(user_id)
            return [_rec_to_response_dict(ar.recommendation) for ar in active_recs]
        except Exception as e:
            logger.exception("list_active failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def update(self, user_id: int, recommendation_id: int, data: RecommendationUpdateRequest) -> dict:
        """
        추천 콘텐츠/선택 여부 수정.

        Args:
            user_id (int): 사용자 ID.
            recommendation_id (int): 수정할 추천 ID.
            data (RecommendationUpdateRequest): 수정할 필드.

        Returns:
            dict: 수정된 추천 응답 딕셔너리.

        Raises:
            HTTPException: 추천 미존재 시 404, 실패 시 500.
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
        추천 비활성화 (status=revoked).

        Args:
            user_id (int): 사용자 ID.
            recommendation_id (int): 비활성화할 추천 ID.

        Raises:
            HTTPException: 추천 미존재 시 404, 실패 시 500.
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
        스캔 기반 추천을 활성으로 반영.

        is_selected=True인 추천 우선, 없으면 전체 반영.

        Args:
            user_id (int): 사용자 ID.
            scan_id (int): 스캔 ID.

        Returns:
            dict: scan_id, saved, saved_count 포함 딕셔너리.

        Raises:
            HTTPException: 실패 시 500.
        """
        try:
            recs = await self.recommendation_repo.list_by_user_scan(user_id=user_id, scan_id=scan_id)
            if not recs:
                generated = await self.get_for_scan(user_id=user_id, scan_id=scan_id)
                ids = [it["id"] for it in (generated.get("items") or [])]
            else:
                ids = [r.id for r in recs]

            selected = [r.id for r in recs if r.is_selected is True]
            target_ids = selected or ids

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
        추천에 피드백 추가.

        Args:
            user_id (int): 사용자 ID.
            recommendation_id (int): 피드백할 추천 ID.
            feedback_type (str): 피드백 타입 (like, dislike, click 등).

        Returns:
            dict: recommendation_id, feedback_type, created_at 포함 딕셔너리.

        Raises:
            HTTPException: 추천 미존재 시 404, 실패 시 500.
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
