from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app


class TestSignupAPI(TestCase):
    """회원가입 API 테스트."""

    async def test_signup_success(self):
        """정상 회원가입 시 201 반환 확인."""
        signup_data = {
            "email": "test@example.com",
            "password": "Password123!",
            "name": "테스터",
            "gender": "MALE",
            "birthday": "1990-01-01",
            "phone_number": "01012345678",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json() == {"detail": "회원가입이 성공적으로 완료되었습니다."}

    async def test_signup_invalid_email(self):
        """유효하지 않은 이메일 형식 시 422 반환 확인."""
        signup_data = {
            "email": "invalid-email",
            "password": "password123!",
            "name": "테스터",
            "gender": "MALE",
            "birthday": "1990-01-01",
            "phone_number": "01012345678",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
