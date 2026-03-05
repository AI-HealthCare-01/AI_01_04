from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app

SIGNUP_DATA = {
    "email": "rec_test@example.com",
    "password": "Password123!",
    "name": "추천테스터",
    "gender": "MALE",
    "birthday": "1990-01-01",
    "phone_number": "01099990000",
}


class TestRecommendationAPI(TestCase):
    async def test_list_recommendations_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/recommendations")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_list_active_recommendations_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/recommendations/active")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_delete_recommendation_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete("/api/v1/recommendations/1")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_list_recommendations_success(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=SIGNUP_DATA)
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": SIGNUP_DATA["email"], "password": SIGNUP_DATA["password"]},
            )
            token = login.json()["access_token"]
            response = await client.get(
                "/api/v1/recommendations",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)

    async def test_list_active_recommendations_success(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=SIGNUP_DATA)
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": SIGNUP_DATA["email"], "password": SIGNUP_DATA["password"]},
            )
            token = login.json()["access_token"]
            response = await client.get(
                "/api/v1/recommendations/active",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.json(), list)
