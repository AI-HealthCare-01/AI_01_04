from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import HTTPException
from starlette import status

from app.dtos.recommendations import RecommendationType, RecommendationUpdateRequest
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.scan_repository import ScanRepository

logger = logging.getLogger(__name__)


def _normalize_rec_type(raw: Any) -> RecommendationType:
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

    async def get_for_scan(self, user_id: int, scan_id: int) -> dict:
        """
        scan 기반 추천 조회/생성 (옵션 A)
        - Recommendation.scan_id 컬럼이 있어야 함
        - 이미 생성된 추천이 있으면 재사용
        """
        scan = await self.scan_repo.get_by_id_for_user(user_id, scan_id)
        if not scan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="scan not found")

        # 1) 이미 scan_id로 생성된 rec가 있으면 재사용
        existing = await self.recommendation_repo.list_by_user_scan(user_id=user_id, scan_id=scan_id)
        if existing:
            return {"scan_id": scan_id, "items": [_rec_to_response_dict(r) for r in existing]}

        diagnosis = scan.get("diagnosis")
        drugs_raw = scan.get("drugs") or []
        drugs: list[str] = drugs_raw if isinstance(drugs_raw, list) else []

        # 2) 배치 생성
        batch = await self.recommendation_repo.create_batch(
            user_id=user_id,
            retrieval_strategy="scan-mvp",
        )

        created: list[Any] = []

        # 3) 진단 기반 추천
        if diagnosis:
            rec = await self.recommendation_repo.create_recommendation(
                user_id=user_id,
                batch_id=batch.id,
                scan_id=scan_id,  # ✅ 옵션 A 핵심
                recommendation_type="followup",
                source="scan.diagnosis",
                content=f"진단명 '{diagnosis}' 기준으로 생활관리/추적 관찰 항목을 확인해보세요.",
                score=0.9,
                rank=1,
                status="active",
            )
            if rec:
                created.append(rec)

        # 4) 약물 기반 추천
        for i, drug in enumerate(drugs[:10], start=1):
            rec = await self.recommendation_repo.create_recommendation(
                user_id=user_id,
                batch_id=batch.id,
                scan_id=scan_id,
                recommendation_type="medication",
                source="scan.drugs",
                content=f"약물 '{drug}' 복용 관련 주의사항/복용법을 확인해보세요.",
                score=0.7,
                rank=10 + i,
                status="active",
            )
            if rec:
                created.append(rec)

        # 5) fallback
        if not created:
            rec = await self.recommendation_repo.create_recommendation(
                user_id=user_id,
                batch_id=batch.id,
                scan_id=scan_id,
                recommendation_type="lifestyle",
                source="scan",
                content="스캔 결과에서 진단/약물 정보를 찾지 못했어요. 텍스트 보정 또는 수동 입력 후 다시 시도해 주세요.",
                score=0.1,
                rank=999,
                status="active",
            )
            if rec:
                created.append(rec)

        return {"scan_id": scan_id, "items": [_rec_to_response_dict(r) for r in created]}

    async def list_by_user(self, user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
        try:
            recs = await self.recommendation_repo.list_by_user(user_id, limit=limit, offset=offset)
            return [_rec_to_response_dict(r) for r in recs]
        except Exception as e:
            logger.exception("list_by_user failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def list_active(self, user_id: int) -> list[dict]:
        try:
            active_recs = await self.recommendation_repo.list_active_for_user(user_id)
            return [_rec_to_response_dict(ar.recommendation) for ar in active_recs]
        except Exception as e:
            logger.exception("list_active failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def update(self, user_id: int, recommendation_id: int, data: RecommendationUpdateRequest) -> dict:
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
        scan 기반 추천을 active로 반영
        - scan_id로 이미 생성된 Recommendation을 가져와서
          is_selected=True 우선, 없으면 전체 반영
        """
        try:
            recs = await self.recommendation_repo.list_by_user_scan(user_id=user_id, scan_id=scan_id)
            if not recs:
                # 없으면 생성부터
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
