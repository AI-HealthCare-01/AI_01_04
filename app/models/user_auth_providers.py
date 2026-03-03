"""
OAuth/소셜 로그인 제공자 정보 (ERD 기반)

📚 학습 포인트:
- ForeignKey: N:1 관계 (한 사용자가 여러 provider를 가질 수 있음)
- 예: 같은 사용자가 Google, Kakao 둘 다로 로그인 가능
"""

from __future__ import annotations

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

from app.models.users import User


class UserAuthProvider(models.Model):
    """
    소셜 로그인 연동 정보 (ERD: user_auth_providers)

    users 테이블과 N:1 관계 (한 사용자 → 여러 provider)
    """

    id = fields.IntField(pk=True)

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="auth_providers",
    )
    provider = fields.CharField(max_length=50)
    provider_user_id = fields.CharField(max_length=255)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_auth_providers"
