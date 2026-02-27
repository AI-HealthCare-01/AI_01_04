from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field

from app.dtos.base import BaseSerializerModel
from app.models.users import Gender, UserRole
from app.validators.common import optional_after_validator
from app.validators.user_validators import validate_birthday, validate_phone_number


class UserUpdateRequest(BaseModel):
    name: Annotated[str | None, Field(None, min_length=2, max_length=100)]
    nickname: Annotated[str | None, Field(None, max_length=50)]
    email: Annotated[EmailStr | None, Field(None, max_length=40)]
    phone_number: Annotated[
        str | None,
        Field(None, description="Available Format: +8201011112222, 01011112222, 010-1111-2222"),
        optional_after_validator(validate_phone_number),
    ]
    birth_date: Annotated[
        date | None,
        Field(None, description="Date Format: YYYY-MM-DD"),
        optional_after_validator(validate_birthday),
    ]
    gender: Annotated[Gender | None, Field(None, description="'MALE' or 'FEMALE'")]


class UserInfoResponse(BaseSerializerModel):
    id: int
    name: str
    nickname: str | None = None
    email: str
    phone_number: str
    birth_date: date | None = None
    gender: Gender | None = None
    role: UserRole
    created_at: datetime
