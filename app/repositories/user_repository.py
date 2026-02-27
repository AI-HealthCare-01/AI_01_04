from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import EmailStr

from app.models.users import Gender, User, UserRole

ALLOWED_UPDATE_FIELDS = ["name", "nickname", "phone_number", "gender", "birth_date"]


class UserRepository:
    def __init__(self):
        self._model = User

    async def get_all(self):
        return await self._model.all()

    async def get_user(self, user_id: int) -> User | None:
        return await self._model.get_or_none(id=user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        return await self._model.get_or_none(email=email)

    async def exists_by_email(self, email: str | EmailStr) -> bool:
        return await self._model.filter(email=email).exists()

    async def exists_by_phone_number(self, phone_number: str) -> bool:
        return await self._model.filter(phone_number=phone_number).exists()

    async def create_user(
        self,
        *,
        email: str | EmailStr,
        name: str,
        phone_number: str,
        birth_date: date | None = None,
        gender: Gender | None = None,
        nickname: str | None = None,
        role: UserRole = UserRole.USER,
    ) -> User:
        return await self._model.create(
            email=email,
            name=name,
            nickname=nickname,
            phone_number=phone_number,
            birth_date=birth_date,
            gender=gender,
            role=role,
        )

    async def update_instance(self, user: User, data: dict[str, Any]) -> None:
        # 허용된 필드만 업데이트
        update_fields: list[str] = []
        for key, value in data.items():
            if key not in ALLOWED_UPDATE_FIELDS:
                continue
            if value is not None:
                setattr(user, key, value)
                update_fields.append(key)

        if update_fields:
            await user.save(update_fields=update_fields)
