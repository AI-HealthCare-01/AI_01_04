"""인증 서비스.

회원가입, 로그인, 이메일/전화번호 중복 검증을 담당한다.
JWT 토큰 발급은 JwtService에 위임한다.
"""

from __future__ import annotations

from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from starlette import status
from tortoise.transactions import in_transaction

from app.dtos.auth import LoginRequest, SignUpRequest
from app.models.users import User
from app.repositories.user_credential_repository import UserCredentialRepository
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService
from app.utils.common import normalize_phone_number
from app.utils.jwt.tokens import AccessToken, RefreshToken
from app.utils.security import hash_password, verify_password


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.credential_repo = UserCredentialRepository()
        self.jwt_service = JwtService()

    async def signup(self, data: SignUpRequest) -> User:
        """회원가입을 처리한다.

        이메일/전화번호 중복 검증 후 사용자를 생성하고,
        비밀번호를 해시하여 user_credentials에 트랜잭션으로 저장한다.

        Args:
            data (SignUpRequest): 이메일, 비밀번호, 이름, 생년월일, 성별, 전화번호가 담긴 요청 데이터.

        Returns:
            User: 생성된 User 객체.

        Raises:
            HTTPException: 이메일 중복(409), 전화번호 중복(409) 시.
        """
        await self.check_email_exists(data.email)

        normalized_phone_number = normalize_phone_number(data.phone_number)
        await self.check_phone_number_exists(normalized_phone_number)
        password_hash = hash_password(data.password)

        async with in_transaction():
            user = await self.user_repo.create_user(
                email=data.email,
                hashed_password=password_hash,
                name=data.name,
                phone_number=normalized_phone_number,
                birthday=data.birthday,
                gender=data.gender,
            )
            await self.credential_repo.create_for_user(
                user=user,
                password_hash=password_hash,
            )
            return user

    async def authenticate(self, data: LoginRequest) -> User:
        """로그인 인증을 수행한다.

        이메일/비밀번호 검증 후 비활성화 계정 여부를 확인한다.

        Args:
            data (LoginRequest): 이메일과 비밀번호가 담긴 로그인 요청 데이터.

        Returns:
            User: 인증된 User 객체.

        Raises:
            HTTPException: 이메일/비밀번호 불일치(400), 비활성화 계정(423) 시.
        """
        email = str(data.email)
        user = await self.user_repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        credential = await self.credential_repo.get_by_user_id(user.id)
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        if not verify_password(data.password, credential.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="비활성화된 계정입니다.")

        return user

    async def login(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        """마지막 로그인 시간을 갱신하고 JWT 토큰 쌍을 발급한다.

        Args:
            user (User): 로그인할 User 객체.

        Returns:
            dict[str, AccessToken | RefreshToken]: access_token과 refresh_token이 담긴 딕셔너리.
        """
        await self.user_repo.update_last_login(user.id)
        return self.jwt_service.issue_jwt_pair(user)

    async def check_email_exists(self, email: str | EmailStr) -> None:
        """이메일 중복 여부를 검증한다.

        Args:
            email (str | EmailStr): 확인할 이메일 주소.

        Raises:
            HTTPException: 이메일이 이미 존재할 시 409.
        """
        if await self.user_repo.exists_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 이메일입니다.")

    async def check_phone_number_exists(self, phone_number: str) -> None:
        """전화번호 중복 여부를 검증한다.

        Args:
            phone_number (str): 확인할 전화번호 (정규화된 값).

        Raises:
            HTTPException: 전화번호가 이미 존재할 시 409.
        """
        if await self.user_repo.exists_by_phone_number(phone_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 휴대폰 번호입니다.")
