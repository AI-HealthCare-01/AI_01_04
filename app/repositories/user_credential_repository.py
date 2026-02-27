from __future__ import annotations

from datetime import datetime

from app.core import config
from app.models.user_credentials import UserCredential
from app.models.users import User


class UserCredentialRepository:
    def __init__(self):
        self._model = UserCredential

    async def get_by_user_id(self, user_id: int) -> UserCredential | None:
        return await self._model.get_or_none(user_id=user_id)

    async def create_for_user(self, user: User, password_hash: str) -> UserCredential:
        return await self._model.create(
            user=user,
            password_hash=password_hash,
            password_updated_at=datetime.now(config.TIMEZONE),
        )

    async def set_password(self, user: User, password_hash: str) -> None:
        cred = await self.get_by_user_id(user.id)
        now = datetime.now(config.TIMEZONE)
        if cred:
            cred.password_hash = password_hash
            cred.password_updated_at = now
            await cred.save(update_fields=["password_hash", "password_updated_at"])
        else:
            await self.create_for_user(user=user, password_hash=password_hash)
