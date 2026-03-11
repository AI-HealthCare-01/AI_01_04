"""사용자 도메인 Repository.

사용자 조회/생성/수정/비활성화를 담당하며,
항상 user_id 스코프로 본인 데이터만 접근 가능하도록 보장한다.
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
        """전체 사용자 목록을 조회한다.

        Returns:
            list[User]: 전체 User 객체 목록.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.all()

    async def get_user(self, user_id: int) -> User | None:
        """ID로 사용자를 단건 조회한다.

        Args:
            user_id (int): 조회할 사용자 ID.

        Returns:
            User | None: User 객체. 존재하지 않으면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.get_or_none(id=user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        """이메일로 사용자를 조회한다.

        Args:
            email (str): 조회할 이메일 주소.

        Returns:
            User | None: User 객체. 존재하지 않으면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.get_or_none(email=email)

    async def exists_by_email(self, email: str | EmailStr) -> bool:
        """이메일 중복 여부를 확인한다.

        Args:
            email (str | EmailStr): 확인할 이메일 주소.

        Returns:
            bool: 이미 존재하면 True, 아니면 False.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.filter(email=email).exists()

    async def exists_by_phone_number(self, phone_number: str) -> bool:
        """휴대폰 번호 중복 여부를 확인한다.

        Args:
            phone_number (str): 확인할 휴대폰 번호.

        Returns:
            bool: 이미 존재하면 True, 아니면 False.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
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
        """새 사용자를 생성한다.

        Args:
            email (str | EmailStr): 이메일 주소.
            name (str): 이름.
            phone_number (str): 정규화된 휴대폰 번호.
            birthday (date): 생년월일.
            gender (Gender | None): 성별. 선택 사항.

        Returns:
            User: 생성된 User 객체.

        Raises:
            IntegrityError: 이메일 또는 휴대폰 번호 중복 시.
            OperationalError: DB 연결 오류 시.
        """
        return await self._model.create(
            email=email,
            name=name,
            phone_number=phone_number,
            birthday=birthday,
            gender=gender,
        )

    async def update_instance(self, user: User, data: dict[str, Any]) -> None:
        """허용된 필드만 선별하여 사용자 정보를 업데이트한다.

        ALLOWED_UPDATE_FIELDS에 없는 필드와 None 값은 무시한다.

        Args:
            user (User): 업데이트할 User 객체.
            data (dict[str, Any]): 업데이트할 필드와 값의 딕셔너리.

        Raises:
            OperationalError: DB 연결 오류 시.
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
        """마지막 로그인 시간을 현재 시각으로 갱신한다.

        Args:
            user_id (int): 갱신할 사용자 ID.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        now = datetime.now(config.TIMEZONE)
        await self._model.filter(id=user_id).update(last_login=now)

    async def deactivate_user(self, user_id: int) -> None:
        """사용자를 비활성화한다 (is_active=False, 실제 삭제 없음).

        Args:
            user_id (int): 비활성화할 사용자 ID.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        await self._model.filter(id=user_id).update(is_active=False)
