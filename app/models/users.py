"""
사용자 관련 모델 (ERD 기반)
- Tortois ORM에서 models.Model을 상속하면 DB 테이블이 됩니다.
- fields.XXXField()가 컬럼을 정의합니다.
- auto_now_add=True: 레코드 생성 시 자동으로 현재
"""
from enum import StrEnum

from tortoise import fields, models


class Gender(StrEnum):
    """성별 (ERD: gender varchar)"""
    MALE = "MALE"
    FEMALE = "FEMALE"


class User(models.Model):
    id = fields.BigIntField(primary_key=True)
    email = fields.CharField(max_length=40)
    hashed_password = fields.CharField(max_length=128)
    name = fields.CharField(max_length=20)
    gender = fields.CharEnumField(enum_type=Gender)
    birthday = fields.DateField()
    phone_number = fields.CharField(max_length=11)
    is_active = fields.BooleanField(default=True)
    is_admin = fields.BooleanField(default=False)
    last_login = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "users"
