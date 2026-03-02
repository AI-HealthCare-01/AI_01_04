from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import EmailStr

from app.core import config
from app.models.user_credentials import UserCredential
from app.models.users import Gender, User, UserRole

ALLOWED_UPDATE_FIELDS = [
    "name",
    "nickname",
    "phone_number",
    "gender",
    "birthday",
    "birth_date",
    "profile_image_url",  # 프로필 업로드
]


class UserRepository:
    def __init__(self):
        self._model = User

    def _has_field(self, field_name: str) -> bool:
        return field_name in self._model._meta.fields_map

    async def get_all(self):
        return await self._model.all()

    async def get_user(self, user_id: int) -> User | None:
        user = await self._model.get_or_none(id=user_id)
        return await self._attach_password_from_credential(user)

    async def get_user_by_email(self, email: str) -> User | None:
        user = await self._model.get_or_none(email=email)
        return await self._attach_password_from_credential(user)

    async def _attach_password_from_credential(self, user: User | None) -> User | None:
        if not user:
            return None
        if self._has_field("hashed_password"):
            return user
        cred = await UserCredential.get_or_none(user_id=user.id)
        if cred:
            # Service(AuthService)가 user.hashed_password를 참조하므로 런타임에 주입
            setattr(user, "hashed_password", cred.password_hash)
        return user

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
        hashed_password: str | None = None,
        birthday: date | None = None,
        birth_date: date | None = None,
        gender: Gender | None = None,
        nickname: str | None = None,
        role: UserRole = UserRole.USER,
        **_: Any,
    ) -> User:
        payload: dict[str, Any] = {
            email=email,
            name=name,
            phone_number=phone_number,
        }

        if nickname is not None and self._has_field("nickname"):
            payload["nickname"] = nickname
        if gender is not None and self._has_field("gender"):
            payload["gender"] = gender

        birthday_value = birthday if birthday is not None else birth_date
        if birthday_value is not None:
            if self._has_field("birthday"):
                payload["birthday"] = birthday_value
            elif self._has_field("birth_date"):
                payload["birth_date"] = birthday_value

        if hashed_password is not None and self._has_field("hashed_password"):
            payload["hashed_password"] = hashed_password
        if self._has_field("role"):
            payload["role"] = role
        if self._has_field("is_active"):
            payload["is_active"] = True
        if self._has_field("deleted_at"):
            payload["deleted_at"] = None

        user = await self._model.create(**payload)

        if hashed_password is not None and not self._has_field("hashed_password"):
            await UserCredential.create(
                user=user,
                password_hash=hashed_password,
                password_updated_at=datetime.now(config.TIMEZONE),
            )
            setattr(user, "hashed_password", hashed_password)

        return user

    async def update_instance(self, user: User, data: dict[str, Any]) -> None:
        update_fields: list[str] = []

        for key, value in data.items():
            if key == "birth_date":
                key = "birthday"
            if key not in ALLOWED_UPDATE_FIELDS:
                continue
            if value is None:
                continue
            if not self._has_field(key):
                continue

            setattr(user, key, value)
            update_fields.append(key)

        if update_fields:
            await user.save(update_fields=update_fields)

    async def deactivate_user(self, user_id: int) -> None:
        now = datetime.now(config.TIMEZONE)
        update_data: dict[str, Any] = {}

        if self._has_field("is_active"):
            update_data["is_active"] = False
        if self._has_field("deleted_at"):
            update_data["deleted_at"] = now

        if update_data:
            await self._model.filter(id=user_id).update(**update_data)

    async def update_last_login(self, user_id: int) -> None:
        if not self._has_field("last_login"):
            return
        await self._model.filter(id=user_id).update(last_login=datetime.now(config.TIMEZONE))
