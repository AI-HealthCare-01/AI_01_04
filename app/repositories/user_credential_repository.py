"""사용자 인증 정보 Repository.

비밀번호 해시 조회/생성/변경을 담당한다.
users 테이블과 1:1 관계이며, OAuth 사용자는 credential이 없을 수 있다.
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
        """user_id로 인증 정보를 조회한다.

        Args:
            user_id (int): 조회할 사용자 ID.

        Returns:
            UserCredential | None: UserCredential 객체. 존재하지 않으면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.get_or_none(user_id=user_id)

    async def create_for_user(self, user: User, password_hash: str) -> UserCredential:
        """사용자의 비밀번호 인증 정보를 생성한다.

        Args:
            user (User): 인증 정보를 생성할 User 객체.
            password_hash (str): bcrypt로 해시된 비밀번호.

        Returns:
            UserCredential: 생성된 UserCredential 객체.

        Raises:
            IntegrityError: 이미 해당 user의 credential이 존재할 시.
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.create(
            user=user,
            password_hash=password_hash,
            password_updated_at=datetime.now(config.TIMEZONE),
        )

    async def set_password(self, user: User, password_hash: str) -> None:
        """비밀번호를 변경한다.

        인증 정보가 이미 존재하면 업데이트하고, 없으면 새로 생성한다.

        Args:
            user (User): 비밀번호를 변경할 User 객체.
            password_hash (str): 새 bcrypt 해시 비밀번호.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        cred = await self.get_by_user_id(user.id)
        now = datetime.now(config.TIMEZONE)
        if cred:
            cred.password_hash = password_hash
            cred.password_updated_at = now
            await cred.save(update_fields=["password_hash", "password_updated_at"])
        else:
            await self.create_for_user(user=user, password_hash=password_hash)
