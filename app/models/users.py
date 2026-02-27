"""
사용자 관련 모델 (ERD 기반)

📚 학습 포인트:
- Tortoise ORM에서 models.Model을 상속하면 DB 테이블이 됩니다.
- fields.XXXField()가 컬럼을 정의합니다.
- auto_now_add=True: 레코드 생성 시 자동으로 현재 시간 저장
"""

from enum import StrEnum

from tortoise import fields, models


class Gender(StrEnum):
    """성별 (ERD: gender varchar)"""

    MALE = "MALE"
    FEMALE = "FEMALE"


class UserRole(StrEnum):
    """사용자 역할 (ERD: role varchar)"""

    USER = "USER"
    ADMIN = "ADMIN"


class User(models.Model):
    """
    사용자 테이블 (ERD: users)

    💡 ERD와 기존 구조 차이:
    - 비밀번호는 user_credentials 테이블로 분리 (보안·OAuth 대응)
    - nickname 추가, phone_number 제거 (ERD 기준)
    """

    id = fields.IntField(pk=True)
    email = fields.CharField(max_length=40, unique=True)
    name = fields.CharField(max_length=100)
    nickname = fields.CharField(max_length=50, null=True)
    phone_number = fields.CharField(max_length=11)
    birth_date = fields.DateField(null=True)
    gender = fields.CharEnumField(enum_type=Gender, null=True)
    role = fields.CharEnumField(enum_type=UserRole, default=UserRole.USER)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"
