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
            birthday="1990-01-01",
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

    async def test_update_success(self):
        from app.dtos.recommendations import RecommendationUpdateRequest

        user = await User.create(email="rec_upd@example.com", name="Test", phone_number="01011112222", birthday="1990-01-01")
        batch = await RecommendationBatch.create(user=user)
        rec = await Recommendation.create(user=user, batch=batch, content="원본", recommendation_type="health")

        service = RecommendationService()
        result = await service.update(user.id, rec.id, RecommendationUpdateRequest(content="수정됨"))

        assert result["content"] == "수정됨"

    async def test_update_not_found(self):
        from fastapi import HTTPException

        from app.dtos.recommendations import RecommendationUpdateRequest

        user = await User.create(email="rec_upd2@example.com", name="Test", phone_number="01011112222", birthday="1990-01-01")
        service = RecommendationService()

        with self.assertRaises(HTTPException) as ctx:
            await service.update(user.id, 9999, RecommendationUpdateRequest(content="수정"))
        assert ctx.exception.status_code == 404

    async def test_delete_success(self):
        user = await User.create(email="rec_del@example.com", name="Test", phone_number="01011112222", birthday="1990-01-01")
        batch = await RecommendationBatch.create(user=user)
        rec = await Recommendation.create(user=user, batch=batch, content="삭제대상", recommendation_type="health")

        service = RecommendationService()
        await service.delete(user.id, rec.id)

        updated = await Recommendation.get(id=rec.id)
        assert updated.status == "revoked"

    async def test_delete_not_found(self):
        from fastapi import HTTPException

        user = await User.create(email="rec_del2@example.com", name="Test", phone_number="01011112222", birthday="1990-01-01")
        service = RecommendationService()

        with self.assertRaises(HTTPException) as ctx:
            await service.delete(user.id, 9999)
        assert ctx.exception.status_code == 404

    async def test_add_feedback_success(self):
        user = await User.create(email="rec_fb@example.com", name="Test", phone_number="01011112222", birthday="1990-01-01")
        batch = await RecommendationBatch.create(user=user)
        rec = await Recommendation.create(user=user, batch=batch, content="피드백대상", recommendation_type="health")

        service = RecommendationService()
        result = await service.add_feedback(user.id, rec.id, feedback_type="like")

        assert result["feedback_type"] == "like"
        assert result["recommendation_id"] == rec.id

    async def test_add_feedback_not_found(self):
        from fastapi import HTTPException

        user = await User.create(email="rec_fb2@example.com", name="Test", phone_number="01011112222", birthday="1990-01-01")
        service = RecommendationService()

        with self.assertRaises(HTTPException) as ctx:
            await service.add_feedback(user.id, 9999, feedback_type="like")
        assert ctx.exception.status_code == 404

    async def test_list_active_success(self):
        user = await User.create(email="rec_active@example.com", name="Test", phone_number="01011112222", birthday="1990-01-01")
        batch = await RecommendationBatch.create(user=user)
        rec = await Recommendation.create(user=user, batch=batch, content="활성추천", recommendation_type="health")
        from app.models.recommendations import UserActiveRecommendation

        await UserActiveRecommendation.create(user=user, recommendation=rec)

        service = RecommendationService()
        result = await service.list_active(user.id)

        assert len(result) == 1
        assert result[0]["content"] == "활성추천"

    async def test_get_for_scan_not_found(self):
        from fastapi import HTTPException

        service = RecommendationService()
        with self.assertRaises(HTTPException) as ctx:
            await service.get_for_scan(user_id=1, scan_id=42)
        assert ctx.exception.status_code == 404

    async def test_save_for_scan_not_found(self):
        from fastapi import HTTPException

        service = RecommendationService()
        with self.assertRaises(HTTPException) as ctx:
            await service.save_for_scan(user_id=1, scan_id=42)
        assert ctx.exception.status_code == 404
