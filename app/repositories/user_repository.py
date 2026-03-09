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
        birthday: date,
        hashed_password: str = "",
        gender: Gender | None = None,
    ) -> User:
        return await self._model.create(
            email=email,
            name=name,
            phone_number=phone_number,
            birthday=birthday,
            hashed_password=hashed_password,
            gender=gender,
        )

    async def update_instance(self, user: User, data: dict[str, Any]) -> None:
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
        now = datetime.now(config.TIMEZONE)
        await self._model.filter(id=user_id).update(last_login=now)

    async def deactivate_user(self, user_id: int) -> None:
        await self._model.filter(id=user_id).update(is_active=False)
