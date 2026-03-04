from __future__ import annotations

import logging

from fastapi import HTTPException

from app.dtos.recommendations import RecommendationUpdateRequest
from app.repositories.recommendation_repository import RecommendationRepository

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self):
        self.recommendation_repo = RecommendationRepository()

    async def get_for_scan(self, user_id: int, scan_id: int) -> dict:
        # TODO: scan_id 소유권 확인 (ScanRepository 필요)
        # TODO: scan 결과 기반 추천 생성 로직 (AI Worker 연동)
        return {
            "scan_id": scan_id,
            "items": [],
        }

    async def list_by_user(self, user_id: int, limit: int = 50, offset: int = 0) -> list:
        """사용자의 추천 목록 조회"""
        try:
            recommendations = await self.recommendation_repo.list_by_user(user_id, limit=limit, offset=offset)
            return [
                {
                    "id": rec.id,
                    "recommendation_type": rec.recommendation_type,
                    "content": rec.content,
                    "score": rec.score,
                    "is_selected": rec.is_selected,
                    "rank": rec.rank,
                    "status": rec.status,
                    "created_at": rec.created_at.isoformat() if rec.created_at else None,
                }
                for rec in recommendations
            ]
        except Exception as e:
            logger.exception("list_by_user failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def list_active(self, user_id: int) -> list:
        """현재 활성화된 추천 목록 조회"""
        try:
            active_recs = await self.recommendation_repo.list_active_for_user(user_id)
            return [
                {
                    "id": ar.recommendation.id,
                    "recommendation_type": ar.recommendation.recommendation_type,
                    "content": ar.recommendation.content,
                    "score": ar.recommendation.score,
                    "assigned_at": ar.assigned_at.isoformat() if ar.assigned_at else None,
                }
                for ar in active_recs
            ]
        except Exception as e:
            logger.exception("list_active failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def update(self, user_id: int, recommendation_id: int, data: RecommendationUpdateRequest) -> dict:
        """추천 내용 업데이트"""
        try:
            rec = await self.recommendation_repo.get_recommendation_for_user(user_id, recommendation_id)
            if not rec:
                raise HTTPException(status_code=404, detail="Recommendation not found")

            update_fields = []
            if data.content is not None:
                rec.content = data.content
                update_fields.append("content")
            if data.is_selected is not None:
                rec.is_selected = data.is_selected
                update_fields.append("is_selected")

            if update_fields:
                await rec.save(update_fields=update_fields)

            return {
                "id": rec.id,
                "content": rec.content,
                "is_selected": rec.is_selected,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("update failed")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def delete(self, user_id: int, recommendation_id: int) -> None:
        """추천 삭제 (status=revoked 처리)"""
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
        # TODO: scan_id 소유권 확인
        # TODO: 선택된 추천들을 active로 반영
        return {
            "scan_id": scan_id,
            "saved": True,
            "saved_count": 0,
        }

    async def add_feedback(self, user_id: int, recommendation_id: int, feedback_type: str) -> dict:
        """추천 피드백 추가 (like, dislike, click 등)"""
        try:
            feedback = await self.recommendation_repo.add_feedback(
                user_id, recommendation_id, feedback_type=feedback_type
            )
            if not feedback:
                raise HTTPException(status_code=404, detail="Recommendation not found")

            return {
                "recommendation_id": recommendation_id,
                "feedback_type": feedback_type,
                "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("add_feedback failed")
            raise HTTPException(status_code=500, detail=str(e)) from e
