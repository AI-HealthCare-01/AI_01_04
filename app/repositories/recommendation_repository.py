"""
추천 도메인 Repository

- RecommendationBatch, Recommendation, UserActiveRecommendation, RecommendationFeedback
- 항상 user_id 스코프: 다른 사용자 추천 조회 불가
"""

from __future__ import annotations

from datetime import datetime

from app.models.recommendations import (
    Recommendation,
    RecommendationBatch,
    RecommendationFeedback,
    UserActiveRecommendation,
)


class RecommendationRepository:
    def __init__(self):
        self._batch_model = RecommendationBatch
        self._rec_model = Recommendation
        self._active_model = UserActiveRecommendation
        self._feedback_model = RecommendationFeedback

    async def get_recommendation_for_user(self, user_id: int, recommendation_id: int) -> Recommendation | None:
        """user_id 소유의 추천만 조회"""
        return await self._rec_model.get_or_none(id=recommendation_id, user_id=user_id)

    async def list_by_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Recommendation]:
        return (
            await self._rec_model.filter(user_id=user_id)
            .order_by("-created_at")
            .offset(offset)
            .limit(limit)
            .prefetch_related("batch")
        )

    async def list_by_date_range(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[Recommendation]:
        return (
            await self._rec_model.filter(
                user_id=user_id,
                created_at__gte=from_dt,
                created_at__lte=to_dt,
            )
            .order_by("created_at")
            .prefetch_related("batch")
        )

    async def list_active_for_user(self, user_id: int) -> list[UserActiveRecommendation]:
        """현재 사용자에게 노출 중인 활성 추천"""
        return await self._active_model.filter(user_id=user_id).prefetch_related("recommendation")

    async def create_batch(
        self,
        user_id: int,
        *,
        retrieval_strategy: str | None = None,
        retrieval_top_k: int | None = None,
        retrieval_lambda: float | None = None,
        llm_model: str | None = None,
        llm_temperature: float | None = None,
        llm_max_tokens: int | None = None,
    ) -> RecommendationBatch:
        return await self._batch_model.create(
            user_id=user_id,
            retrieval_strategy=retrieval_strategy,
            retrieval_top_k=retrieval_top_k,
            retrieval_lambda=retrieval_lambda,
            llm_model=llm_model,
            llm_temperature=llm_temperature,
            llm_max_tokens=llm_max_tokens,
        )

    async def create_recommendation(
        self,
        user_id: int,
        batch_id: int,
        *,
        scan_id: int | None = None,  # ✅ 추가
        recommendation_type: str | None = None,
        source: str | None = None,
        content: str | None = None,
        score: float | None = None,
        rank: int | None = None,
        status: str | None = None,
        feature_snapshot_id: int | None = None,
    ) -> Recommendation | None:
        batch = await self._batch_model.get_or_none(id=batch_id, user_id=user_id)
        if not batch:
            return None
        return await self._rec_model.create(
            user_id=user_id,
            batch=batch,
            scan_id=scan_id,  # ✅ 추가
            recommendation_type=recommendation_type,
            source=source,
            content=content,
            score=score,
            rank=rank,
            status=status,
            feature_snapshot_id=feature_snapshot_id,
        )

    async def get_active_for_recommendation(self, user_id: int, recommendation_id: int) -> UserActiveRecommendation | None:
        """이미 active 할당된 추천인지 확인"""
        return await self._active_model.get_or_none(user_id=user_id, recommendation_id=recommendation_id)

    async def assign_active(self, user_id: int, recommendation_id: int) -> UserActiveRecommendation | None:
        """추천을 사용자에게 활성 할당 (user 소유 추천인지 검증)"""
        rec = await self.get_recommendation_for_user(user_id, recommendation_id)
        if not rec:
            return None
        return await self._active_model.create(user_id=user_id, recommendation=rec)

    async def add_feedback(
        self,
        user_id: int,
        recommendation_id: int,
        *,
        feedback_type: str,
    ) -> RecommendationFeedback | None:
        """추천 피드백 (user 소유 추천인지 검증)"""
        rec = await self.get_recommendation_for_user(user_id, recommendation_id)
        if not rec:
            return None
        return await self._feedback_model.create(
            recommendation=rec,
            user_id=user_id,
            feedback_type=feedback_type,
        )

    async def clear_active_for_user(self, user_id: int) -> int:
        return await self._active_model.filter(user_id=user_id).delete()

    async def assign_active_many(self, user_id: int, recommendation_ids: list[int]) -> None:
        # user 소유 검증은 create 전에 각 rec 확인하거나, filter로 한 번에 가져와서 처리
        recs = await self._rec_model.filter(user_id=user_id, id__in=recommendation_ids).all()
        for rec in recs:
            await self._active_model.create(user_id=user_id, recommendation=rec)

    async def list_by_scan_for_user(self, user_id: int, scan_id: int) -> list[Recommendation]:
        """
        같은 scan_id로 생성된 추천이 이미 있으면 재사용하기 위한 조회
        """
        return await self._rec_model.filter(user_id=user_id, scan_id=scan_id).order_by("rank", "id").all()

    async def list_by_user_scan(self, user_id: int, scan_id: int) -> list[Recommendation]:
        return (
            await self._rec_model.filter(user_id=user_id, scan_id=scan_id)
            .order_by("rank", "-created_at")
            .prefetch_related("batch")
        )
