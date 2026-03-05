import io

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app

SIGNUP_DATA = {
    "email": "scan_test@example.com",
    "password": "Password123!",
    "name": "스캔테스터",
    "gender": "MALE",
    "birthday": "1990-01-01",
    "phone_number": "01077778888",
}


class TestScanAPI(TestCase):
    async def test_upload_scan_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/scans/upload", files={"file": ("test.jpg", b"data", "image/jpeg")})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_scan_result_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/scans/1")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_analyze_scan_unauthorized(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/scans/1/analyze")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_upload_scan_success(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=SIGNUP_DATA)
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": SIGNUP_DATA["email"], "password": SIGNUP_DATA["password"]},
            )
            token = login.json()["access_token"]
            fake_image = io.BytesIO(b"fake image content")
            response = await client.post(
                "/api/v1/scans/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("prescription.jpg", fake_image, "image/jpeg")},
            )
        assert response.status_code == status.HTTP_201_CREATED
        assert "scan_id" in response.json()
