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
        self.cred_repo = UserCredentialRepository()
        self.jwt_service = JwtService()

    async def signup(self, data: SignUpRequest) -> User:
        await self.check_email_exists(data.email)

        normalized_phone_number = normalize_phone_number(data.phone_number)
        await self.check_phone_number_exists(normalized_phone_number)

        async with in_transaction():
            user = await self.user_repo.create_user(
                email=data.email,
                name=data.name,
                phone_number=normalized_phone_number,
                gender=data.gender,
                birth_date=data.birth_date,
                # nickname은 DTO에 있으면 넣고 없으면 None
            )
            await self.cred_repo.create_for_user(user=user, password_hash=hash_password(data.password))
            return user

    async def authenticate(self, data: LoginRequest) -> User:
        email = str(data.email)
        user = await self.user_repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        cred = await self.cred_repo.get_by_user_id(user.id)
        if not cred:
            # OAuth 유저 등 비밀번호 없는 케이스
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        if not verify_password(data.password, cred.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        return user

    async def login(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        # User 모델에 last_login이 없어서 update_last_login 제거
        return self.jwt_service.issue_jwt_pair(user)

    async def check_email_exists(self, email: str | EmailStr) -> None:
        if await self.user_repo.exists_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 이메일입니다.")

    async def check_phone_number_exists(self, phone_number: str) -> None:
        if await self.user_repo.exists_by_phone_number(phone_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 휴대폰 번호입니다.")
