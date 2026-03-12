"""추천 도메인 Repository.

RecommendationBatch, Recommendation, UserActiveRecommendation, RecommendationFeedback
조회/생성/업데이트를 담당한다.
항상 user_id 스코프로 다른 사용자 추천 접근을 차단한다.
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
        """user_id 소유의 추천을 단건 조회한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            recommendation_id (int): 조회할 추천 ID.

        Returns:
            Recommendation | None: Recommendation 객체. 없거나 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._rec_model.get_or_none(id=recommendation_id, user_id=user_id)

    async def list_by_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Recommendation]:
        """사용자의 추천 목록을 최신순으로 조회한다.

        Args:
            user_id (int): 조회할 사용자 ID.
            limit (int): 최대 반환 건수. 기본값 50.
            offset (int): 건너뛸 건수. 기본값 0.

        Returns:
            list[Recommendation]: batch가 prefetch된 Recommendation 목록 (최신순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """기간 내 추천 목록을 조회한다 (created_at 기준).

        Args:
            user_id (int): 조회할 사용자 ID.
            from_dt (datetime): 조회 시작 시각 (포함).
            to_dt (datetime): 조회 종료 시각 (포함).

        Returns:
            list[Recommendation]: 기간 내 Recommendation 목록 (시간 오름차순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """현재 사용자에게 노출 중인 활성 추천 목록을 조회한다.

        Args:
            user_id (int): 조회할 사용자 ID.

        Returns:
            list[UserActiveRecommendation]: recommendation이 prefetch된 UserActiveRecommendation 목록.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """추천 배치를 생성한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            retrieval_strategy (str | None): 검색 전략 이름. 선택 사항.
            retrieval_top_k (int | None): 검색 상위 K개. 선택 사항.
            retrieval_lambda (float | None): 검색 람다 파라미터. 선택 사항.
            llm_model (str | None): 사용한 LLM 모델명. 선택 사항.
            llm_temperature (float | None): LLM temperature. 선택 사항.
            llm_max_tokens (int | None): LLM 최대 토큰 수. 선택 사항.

        Returns:
            RecommendationBatch: 생성된 RecommendationBatch 객체.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        scan_id: int | None = None,
        recommendation_type: str | None = None,
        source: str | None = None,
        content: str | None = None,
        score: float | None = None,
        rank: int | None = None,
        status: str | None = None,
        feature_snapshot_id: int | None = None,
    ) -> Recommendation | None:
        """개별 추천을 생성한다 (batch가 user 소유인지 검증).

        Args:
            user_id (int): 소유자 사용자 ID.
            batch_id (int): 추천 배치 ID.
            scan_id (int | None): 연관 스캔 ID. 선택 사항.
            recommendation_type (str | None): 추천 유형 (lifestyle, medication 등). 선택 사항.
            source (str | None): 추천 출처 (vector.disease_guideline 등). 선택 사항.
            content (str | None): 추천 내용. 선택 사항.
            score (float | None): 유사도 점수. 선택 사항.
            rank (int | None): 추천 순위. 선택 사항.
            status (str | None): 추천 상태 (active, revoked 등). 선택 사항.
            feature_snapshot_id (int | None): 사용자 피처 스냅샷 ID. 선택 사항.

        Returns:
            Recommendation | None: 생성된 Recommendation 객체. batch 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        batch = await self._batch_model.get_or_none(id=batch_id, user_id=user_id)
        if not batch:
            return None
        return await self._rec_model.create(
            user_id=user_id,
            batch=batch,
            scan_id=scan_id,
            recommendation_type=recommendation_type,
            source=source,
            content=content,
            score=score,
            rank=rank,
            status=status,
            feature_snapshot_id=feature_snapshot_id,
        )

    async def get_active_for_recommendation(
        self, user_id: int, recommendation_id: int
    ) -> UserActiveRecommendation | None:
        """이미 활성 할당된 추천인지 확인한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            recommendation_id (int): 확인할 추천 ID.

        Returns:
            UserActiveRecommendation | None: 활성 추천 객체. 없으면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._active_model.get_or_none(user_id=user_id, recommendation_id=recommendation_id)

    async def assign_active(self, user_id: int, recommendation_id: int) -> UserActiveRecommendation | None:
        """추천을 사용자에게 활성 할당한다 (user 소유 추천인지 검증).

        Args:
            user_id (int): 소유자 사용자 ID.
            recommendation_id (int): 활성 할당할 추천 ID.

        Returns:
            UserActiveRecommendation | None: 생성된 UserActiveRecommendation 객체. 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """추천에 피드백을 추가한다 (user 소유 추천인지 검증).

        Args:
            user_id (int): 소유자 사용자 ID.
            recommendation_id (int): 피드백을 추가할 추천 ID.
            feedback_type (str): 피드백 유형 (like, dislike, click).

        Returns:
            RecommendationFeedback | None: 생성된 RecommendationFeedback 객체. 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        rec = await self.get_recommendation_for_user(user_id, recommendation_id)
        if not rec:
            return None
        return await self._feedback_model.create(
            recommendation=rec,
            user_id=user_id,
            feedback_type=feedback_type,
        )

    async def clear_active_for_user(self, user_id: int) -> int:
        """사용자의 모든 활성 추천을 삭제한다.

        Args:
            user_id (int): 삭제할 사용자 ID.

        Returns:
            int: 삭제된 행 수.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._active_model.filter(user_id=user_id).delete()

    async def assign_active_many(self, user_id: int, recommendation_ids: list[int]) -> None:
        """여러 추천을 사용자에게 일괄 활성 할당한다 (user 소유 추천만 처리).

        Args:
            user_id (int): 소유자 사용자 ID.
            recommendation_ids (list[int]): 활성 할당할 추천 ID 목록.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        recs = await self._rec_model.filter(user_id=user_id, id__in=recommendation_ids).all()
        for rec in recs:
            await self._active_model.create(user_id=user_id, recommendation=rec)

    async def list_by_user_scan(self, user_id: int, scan_id: int) -> list[Recommendation]:
        """특정 스캔에 연관된 추천 목록을 조회한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            scan_id (int): 조회할 스캔 ID.

        Returns:
            list[Recommendation]: batch가 prefetch된 Recommendation 목록 (rank 오름차순, 최신순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return (
            await self._rec_model.filter(user_id=user_id, scan_id=scan_id)
            .order_by("rank", "-created_at")
            .prefetch_related("batch")
        )
