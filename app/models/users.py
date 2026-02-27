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
    id = fields.BigIntField(pk=True)

    email = fields.CharField(max_length=40, unique=True)
    hashed_password = fields.CharField(max_length=128)

    name = fields.CharField(max_length=20)
    gender = fields.CharEnumField(enum_type=Gender)
    birthday = fields.DateField()

    phone_number = fields.CharField(max_length=11)

    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)

    last_login = fields.DatetimeField(null=True)

    # ✅ 추가: 프로필 이미지 URL (요구사항)
    profile_image_url = fields.CharField(max_length=500, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"
