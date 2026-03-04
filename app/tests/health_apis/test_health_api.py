from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app

SIGNUP_DATA = {
    "email": "health_test@example.com",
    "password": "Password123!",
    "name": "건강테스터",
    "gender": "FEMALE",
    "birthday": "1990-01-01",
    "phone_number": "01033334444",
}


class TestHealthAPI(TestCase):
    async def test_get_health_history_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/history")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_health_day_detail_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/health/history/2024-01-01")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_update_health_log_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.patch("/api/v1/health/logs/1", json={"status": "done"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_health_history_success(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=SIGNUP_DATA)
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": SIGNUP_DATA["email"], "password": SIGNUP_DATA["password"]},
            )
            token = login.json()["access_token"]
            response = await client.get(
                "/api/v1/health/history",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert "items" in response.json()
