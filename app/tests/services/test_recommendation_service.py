from __future__ import annotations

from tortoise.contrib.test import TestCase

from app.models.recommendations import Recommendation, RecommendationBatch
from app.models.users import User
from app.services.recommendations import RecommendationService


class TestRecommendationService(TestCase):
    async def test_list_by_user(self):
        """사용자의 추천 목록 조회"""
        user = await User.create(
            email="test@example.com",
            name="Test User",
            phone_number="01012345678",
        )
        batch = await RecommendationBatch.create(user=user)
        await Recommendation.create(
            user=user,
            batch=batch,
            recommendation_type="health",
            content="건강 추천",
            score=0.9,
        )

        service = RecommendationService()
        result = await service.list_by_user(user.id, limit=10)

        assert len(result) == 1
        assert result[0]["content"] == "건강 추천"
