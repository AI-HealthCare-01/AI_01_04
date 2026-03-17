"""
사용자 모델 (ERD: users)

- 이메일/전화번호 유니크 제약
- 비밀번호는 user_credentials 테이블에 분리 저장
"""

from __future__ import annotations

from enum import StrEnum

from tortoise import fields, models


class UserRole(StrEnum):
    """사용자 역할 열거형."""

    USER = "USER"
    ADMIN = "ADMIN"


class Gender(StrEnum):
    """성별 열거형."""

    MALE = "MALE"
    FEMALE = "FEMALE"


class User(models.Model):
    """
    사용자 모델 (ERD: users).

    이메일/전화번호 유니크 제약, 비밀번호는 user_credentials 테이블에 분리 저장.
    """

    id = fields.IntField(pk=True)

    email = fields.CharField(max_length=40, unique=True)
    hashed_password = fields.CharField(max_length=128, null=True)
    name = fields.CharField(max_length=100)
    phone_number = fields.CharField(max_length=11)
    birthday = fields.DateField()
    gender = fields.CharEnumField(enum_type=Gender, null=True)
    hashed_password = fields.CharField(max_length=128, default="")

    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    profile_image_url = fields.CharField(max_length=500, null=True)
    last_login = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"
