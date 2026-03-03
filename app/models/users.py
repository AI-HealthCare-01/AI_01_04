from __future__ import annotations

from enum import StrEnum

from tortoise import fields, models


class UserRole(StrEnum):
    USER = "USER"
    ADMIN = "ADMIN"


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class User(models.Model):
    """사용자 모델 (ERD: users)"""

    id = fields.IntField(pk=True)

    email = fields.CharField(max_length=40, unique=True)
    name = fields.CharField(max_length=100)
    nickname = fields.CharField(max_length=50, null=True)
    phone_number = fields.CharField(max_length=11)
    birth_date = fields.DateField(null=True)
    gender = fields.CharEnumField(enum_type=Gender, null=True)
    role = fields.CharEnumField(enum_type=UserRole, default=UserRole.USER)

    is_active = fields.BooleanField(default=True)
    profile_image_url = fields.CharField(max_length=500, null=True)
    last_login = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"
