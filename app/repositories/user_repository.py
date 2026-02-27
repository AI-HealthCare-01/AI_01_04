from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import EmailStr

from app.core import config
from app.models.users import Gender, User, UserRole

ALLOWED_UPDATE_FIELDS = [
    "name",
    "nickname",
    "phone_number",
    "gender",
    "birth_date",
    "profile_image_url",  # 프로필 업로드
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
        birth_date: date | None = None,
        gender: Gender | None = None,
        nickname: str | None = None,
        role: UserRole = UserRole.USER,
        # ✅ 만약 init migration에 is_admin이 있으면 여기도 받을 수 있음
        # is_admin: bool = False,
    ) -> User:
        return await self._model.create(
            email=email,
            name=name,
            nickname=nickname,
            phone_number=phone_number,
            birth_date=birth_date,
            gender=gender,
            role=role,
            # is_admin=is_admin,
            is_active=True,  # ✅ 컬럼 존재 시 명시적으로
            deleted_at=None,  # ✅ 컬럼 존재 시 명시적으로
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

    async def deactivate_user(self, user_id: int) -> None:
        # ✅ soft delete 정책: is_active=False + deleted_at 기록
        now = datetime.now(config.TIMEZONE)

        # deleted_at 컬럼이 진짜로 있는 경우에만 update에 포함해야 함
        # (없으면 migration/모델부터 맞춰야 함)
        await self._model.filter(id=user_id).update(is_active=False, deleted_at=now)
