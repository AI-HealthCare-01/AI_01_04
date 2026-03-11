"""
사용자 도메인 Repository

- 사용자 조회/생성/수정/비활성화 담당
- 항상 user_id 스코프: 본인 데이터만 접근 가능
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import EmailStr

from app.core import config
from app.models.users import Gender, User

ALLOWED_UPDATE_FIELDS = [
    "name",
    "email",
    "phone_number",
    "gender",
    "birthday",
    "profile_image_url",
]


class UserRepository:
    def __init__(self):
        self._model = User

    async def get_all(self) -> list[User]:
        """전체 사용자 목록 조회"""
        return await self._model.all()

    async def get_user(self, user_id: int) -> User | None:
        """ID로 사용자 단건 조회. 없으면 None 반환"""
        return await self._model.get_or_none(id=user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        """이메일로 사용자 조회. 없으면 None 반환"""
        return await self._model.get_or_none(email=email)

    async def exists_by_email(self, email: str | EmailStr) -> bool:
        """이메일 중복 여부 확인"""
        return await self._model.filter(email=email).exists()

    async def exists_by_phone_number(self, phone_number: str) -> bool:
        """휴대폰 번호 중복 여부 확인"""
        return await self._model.filter(phone_number=phone_number).exists()

    async def create_user(
        self,
        *,
        email: str | EmailStr,
        name: str,
        phone_number: str,
        birthday: date,
        gender: Gender | None = None,
    ) -> User:
        return await self._model.create(
            email=email,
            name=name,
            phone_number=phone_number,
            birthday=birthday,
            gender=gender,
        )

    async def update_instance(self, user: User, data: dict[str, Any]) -> None:
        """
        허용된 필드만 선별하여 사용자 정보 업데이트

        - ALLOWED_UPDATE_FIELDS에 없는 필드는 무시
        - None 값은 업데이트 제외
        """
        update_fields: list[str] = []

        for key, value in data.items():
            if key not in ALLOWED_UPDATE_FIELDS:
                continue
            if value is None:
                continue

            setattr(user, key, value)
            update_fields.append(key)

        if update_fields:
            await user.save(update_fields=update_fields)

    async def update_last_login(self, user_id: int) -> None:
        """마지막 로그인 시간 갱신"""
        now = datetime.now(config.TIMEZONE)
        await self._model.filter(id=user_id).update(last_login=now)

    async def deactivate_user(self, user_id: int) -> None:
        """사용자 비활성화 (is_active=False)"""
        await self._model.filter(id=user_id).update(is_active=False)
