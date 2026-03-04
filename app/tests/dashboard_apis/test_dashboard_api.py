from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app

SIGNUP_DATA = {
    "email": "dashboard_test@example.com",
    "password": "Password123!",
    "name": "대시보드테스터",
    "gender": "MALE",
    "birthday": "1990-01-01",
    "phone_number": "01055556666",
}


class TestDashboardAPI(TestCase):
    async def test_get_dashboard_summary_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/dashboard/summary")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_dashboard_summary_success(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=SIGNUP_DATA)
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": SIGNUP_DATA["email"], "password": SIGNUP_DATA["password"]},
            )
            token = login.json()["access_token"]
            response = await client.get(
                "/api/v1/dashboard/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_200_OK
