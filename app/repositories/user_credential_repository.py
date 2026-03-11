"""
사용자 인증 정보 Repository

- 비밀번호 해시 조회/생성/변경 담당
- users 테이블과 1:1 관계
"""

from __future__ import annotations

from datetime import datetime

from app.core import config
from app.models.user_credentials import UserCredential
from app.models.users import User


class UserCredentialRepository:
    def __init__(self):
        self._model = UserCredential

    async def get_by_user_id(self, user_id: int) -> UserCredential | None:
        """user_id로 인증 정보 조회. 없으면 None 반환"""
        return await self._model.get_or_none(user_id=user_id)

    async def create_for_user(self, user: User, password_hash: str) -> UserCredential:
        """사용자의 비밀번호 인증 정보 생성"""
        return await self._model.create(
            user=user,
            password_hash=password_hash,
            password_updated_at=datetime.now(config.TIMEZONE),
        )

    async def set_password(self, user: User, password_hash: str) -> None:
        """
        비밀번호 변경

        - 인증 정보가 있으면 업데이트, 없으면 새로 생성
        """
        cred = await self.get_by_user_id(user.id)
        now = datetime.now(config.TIMEZONE)
        if cred:
            cred.password_hash = password_hash
            cred.password_updated_at = now
            await cred.save(update_fields=["password_hash", "password_updated_at"])
        else:
            await self.create_for_user(user=user, password_hash=password_hash)
