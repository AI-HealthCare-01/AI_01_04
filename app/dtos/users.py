from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.dtos.base import BaseSerializerModel
from app.models.users import Gender, User, UserRole
from app.validators.common import optional_after_validator
from app.validators.user_validators import validate_birthday, validate_phone_number


class UserUpdateRequest(BaseModel):
    name: Annotated[str | None, Field(None, min_length=2, max_length=100)]
    email: Annotated[EmailStr | None, Field(None, max_length=40)]
    phone_number: Annotated[
        str | None,
        Field(None, description="Available Format: +8201011112222, 01011112222, 010-1111-2222"),
        optional_after_validator(validate_phone_number),
    ]
    birthday: Annotated[
        date | None,
        Field(None, description="Date Format: YYYY-MM-DD"),
        optional_after_validator(validate_birthday),
    ]
    gender: Annotated[Gender | None, Field(None, description="'MALE' or 'FEMALE'")]

    # 스키마에 profile_image_url 없음 - 향후 마이그레이션 시 사용
    profile_image_url: Annotated[str | None, Field(None, max_length=500)]


class UserInfoResponse(BaseSerializerModel):
    """User 모델 → API 응답 (birth_date→birthday, role→is_admin 등 매핑)"""

    id: int
    name: str
    email: str
    phone_number: str
    birthday: date | None = None
    gender: Gender | None = None
    is_active: bool = True
    is_admin: bool = False
    last_login: datetime | None = None
    profile_image_url: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_user(cls, user: User) -> "UserInfoResponse":
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            phone_number=user.phone_number,
            birthday=user.birth_date,
            gender=user.gender,
            is_active=user.is_active,
            is_admin=user.role == UserRole.ADMIN,
            last_login=user.last_login,
            profile_image_url=user.profile_image_url,
            created_at=user.created_at,
            updated_at=user.updated_at or user.created_at,
        )
