from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.models.users import Gender
from app.validators.user_validators import validate_birthday, validate_password, validate_phone_number


class SignUpRequest(BaseModel):
    """신규 회원가입 요청 스키마."""

    email: Annotated[EmailStr, Field(..., max_length=40)]
    password: Annotated[str, Field(min_length=8), AfterValidator(validate_password)]
    name: Annotated[str, Field(..., max_length=20)]
    gender: Gender
    birthday: Annotated[date, AfterValidator(validate_birthday)]
    phone_number: Annotated[str, AfterValidator(validate_phone_number)]


class LoginRequest(BaseModel):
    """로그인 요청 스키마."""

    email: EmailStr
    password: Annotated[str, Field(min_length=8)]


class LoginResponse(BaseModel):
    """로그인 응답 스키마 - access_token 포함."""

    access_token: str


class TokenRefreshResponse(LoginResponse):
    """토큰 갱신 응답 스키마 - 새 access_token 포함."""
