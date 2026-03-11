from __future__ import annotations

from tortoise.contrib.test import TestCase

from app.models.recommendations import Recommendation, RecommendationBatch
from app.models.users import User
from app.repositories.recommendation_repository import RecommendationRepository


class TestRecommendationRepository(TestCase):
    async def test_get_recommendation_for_user(self):
        """user_id 소유의 추천만 조회"""
        user = await User.create(
            email="test@example.com",
            name="Test User",
            phone_number="01012345678",
            birthday="1990-01-01",
        )
        batch = await RecommendationBatch.create(user=user)
        rec = await Recommendation.create(
            user=user,
            batch=batch,
            recommendation_type="health",
            content="테스트 추천",
            score=0.9,
        )

        repo = RecommendationRepository()
        result = await repo.get_recommendation_for_user(user.id, rec.id)

        assert result is not None
        assert result.id == rec.id

        # 다른 사용자는 조회 불가
        result2 = await repo.get_recommendation_for_user(999, rec.id)
        assert result2 is None
