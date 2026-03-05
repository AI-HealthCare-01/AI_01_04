from __future__ import annotations

from datetime import date

from tortoise.contrib.test import TestCase

from app.dtos.auth import LoginRequest, SignUpRequest
from app.models.users import Gender, User
from app.services.auth import AuthService
from app.utils.security import hash_password

SIGNUP_DATA = SignUpRequest(
    email="auth_svc@example.com",
    password="Password123!",
    name="테스터",
    gender=Gender.MALE,
    birthday=date(1990, 1, 1),
    phone_number="01011112222",
)


class TestAuthService(TestCase):
    async def test_signup_success(self):
        service = AuthService()
        user = await service.signup(SIGNUP_DATA)
        assert user.email == "auth_svc@example.com"

    async def test_signup_duplicate_email_raises(self):
        from fastapi import HTTPException

        service = AuthService()
        await service.signup(SIGNUP_DATA)
        with self.assertRaises(HTTPException) as ctx:
            await service.signup(
                SignUpRequest(
                    email="auth_svc@example.com",
                    password="Password123!",
                    name="다른사람",
                    gender=Gender.MALE,
                    birthday=date(1990, 1, 1),
                    phone_number="01099998888",
                )
            )
        assert ctx.exception.status_code == 409

    async def test_signup_duplicate_phone_raises(self):
        from fastapi import HTTPException

        service = AuthService()
        await service.signup(SIGNUP_DATA)
        with self.assertRaises(HTTPException) as ctx:
            await service.signup(
                SignUpRequest(
                    email="other@example.com",
                    password="Password123!",
                    name="다른사람",
                    gender=Gender.MALE,
                    birthday=date(1990, 1, 1),
                    phone_number="01011112222",
                )
            )
        assert ctx.exception.status_code == 409

    async def test_authenticate_no_credential_raises(self):
        from fastapi import HTTPException

        # credential 없이 user만 생성
        await User.create(email="nocred@example.com", name="테스터", phone_number="01022223333")
        service = AuthService()
        with self.assertRaises(HTTPException) as ctx:
            await service.authenticate(LoginRequest(email="nocred@example.com", password="Password123!"))
        assert ctx.exception.status_code == 400

    async def test_authenticate_inactive_user_raises(self):
        from fastapi import HTTPException

        from app.models.user_credentials import UserCredential

        user = await User.create(
            email="inactive@example.com", name="테스터", phone_number="01033334444", is_active=False
        )
        await UserCredential.create(user=user, password_hash=hash_password("Password123!"))
        service = AuthService()
        with self.assertRaises(HTTPException) as ctx:
            await service.authenticate(LoginRequest(email="inactive@example.com", password="Password123!"))
        assert ctx.exception.status_code == 423
