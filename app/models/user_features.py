"""
사용자 피처/특성 스냅샷 (ERD 기반)

📚 학습 포인트:
- feature_json: 추천 모델 입력용 사용자 특성 (나이, 질병, 복용약 등)
- 스냅샷: 특정 시점의 상태 저장 (추천 생성 시점 복원용)
- user_current_features: 현재 최신 상태만 유지 (1:1)
"""

from __future__ import annotations

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation, OneToOneRelation

from app.models.users import User


class UserFeatureSnapshot(models.Model):
    """
    사용자 피처 스냅샷 (ERD: user_feature_snapshots)

    추천 생성 시점의 사용자 상태를 저장
    """

    id = fields.IntField(pk=True)

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="feature_snapshots",
    )
    feature_json = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_feature_snapshots"


class UserCurrentFeatures(models.Model):
    """
    사용자 현재 피처 (ERD: user_current_features)

    user_id가 PK (1:1 관계, 항상 최신만 유지)
    """

    user: OneToOneRelation[User] = fields.OneToOneField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="current_features",
        pk=True,
    )
    feature_json = fields.TextField()
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_current_features"
