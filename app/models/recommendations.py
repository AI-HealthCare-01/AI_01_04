"""
추천 시스템 모델 (ERD 기반)

📚 학습 포인트:
- recommendation_batches: 한 번의 추천 요청에서 여러 개 생성
- recommendations: 개별 추천 결과 (rank, score, A/B 테스트용 model_version 등)
- user_active_recommendations: 사용자에게 현재 노출 중인 추천 (N:N 중간 테이블)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

if TYPE_CHECKING:
    from app.models.user_features import UserFeatureSnapshot
    from app.models.users import User


class RecommendationBatch(models.Model):
    """
    추천 배치 (ERD: recommendation_batches)

    한 번의 추천 요청 파라미터와 결과물 묶음
    """

    id = fields.IntField(pk=True)

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="recommendation_batches",
    )

    retrieval_strategy = fields.CharField(max_length=100, null=True)
    retrieval_top_k = fields.IntField(null=True)
    retrieval_lambda = fields.FloatField(null=True)
    llm_model = fields.CharField(max_length=100, null=True)
    llm_temperature = fields.FloatField(null=True)
    llm_max_tokens = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "recommendation_batches"


class Recommendation(models.Model):
    """
    개별 추천 결과 (ERD: recommendations)
    """

    id = fields.IntField(pk=True)

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="recommendations",
    )

    feature_snapshot: ForeignKeyRelation[UserFeatureSnapshot] | None = fields.ForeignKeyField(
        "models.UserFeatureSnapshot",
        on_delete=fields.SET_NULL,
        null=True,
        related_name="recommendations",
    )

    batch: ForeignKeyRelation[RecommendationBatch] = fields.ForeignKeyField(
        "models.RecommendationBatch",
        on_delete=fields.CASCADE,
        related_name="recommendations",
    )

    recommendation_type = fields.CharField(max_length=50, null=True)
    source = fields.CharField(max_length=100, null=True)
    content = fields.TextField(null=True)
    score = fields.FloatField(null=True)
    is_selected = fields.BooleanField(null=True)
    rank = fields.IntField(null=True)
    status = fields.CharField(max_length=50, null=True)
    model_version = fields.CharField(max_length=50, null=True)
    prompt_version = fields.CharField(max_length=50, null=True)
    embedding_model_version = fields.CharField(max_length=50, null=True)
    expiration_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "recommendations"


class UserActiveRecommendation(models.Model):
    """
    사용자 활성 추천 (ERD: user_active_recommendations)

    현재 사용자에게 노출 중인 추천 (user ↔ recommendation N:N)
    ERD에는 id 없지만 Tortoise 호환을 위해 추가
    """

    id = fields.IntField(pk=True)

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="active_recommendations",
    )

    recommendation: ForeignKeyRelation[Recommendation] = fields.ForeignKeyField(
        "models.Recommendation",
        on_delete=fields.CASCADE,
        related_name="active_users",
    )

    assigned_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_active_recommendations"


class RecommendationFeedback(models.Model):
    """
    추천 피드백 (ERD: recommendation_feedback)

    사용자가 추천에 대해 좋아요/싫어요 등 반응 기록
    """

    id = fields.IntField(pk=True)

    recommendation: ForeignKeyRelation[Recommendation] = fields.ForeignKeyField(
        "models.Recommendation",
        on_delete=fields.CASCADE,
        related_name="feedbacks",
    )

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="recommendation_feedbacks",
    )

    feedback_type = fields.CharField(max_length=50)  # like, dislike, click 등
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "recommendation_feedback"
