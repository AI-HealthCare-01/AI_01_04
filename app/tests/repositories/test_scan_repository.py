from __future__ import annotations

from tortoise.contrib.test import TestCase

from app.models.users import User
from app.repositories.scan_repository import ScanRepository


class TestScanRepository(TestCase):
    async def test_create_and_get_scan(self):
        """스캔 생성 및 조회"""
        user = await User.create(email="scan_repo@example.com", name="테스터", phone_number="01011112222", birthday="1990-01-01")
        repo = ScanRepository()
        scan = await repo.create(user_id=user.id, file_path="test.jpg")

        assert scan["scan_id"] is not None
        assert scan["user_id"] == user.id
        assert scan["status"] == "uploaded"

        # 조회
        result = await repo.get_by_id_for_user(user.id, scan["scan_id"])
        assert result is not None
        assert result["scan_id"] == scan["scan_id"]

        # 다른 사용자는 조회 불가
        result2 = await repo.get_by_id_for_user(user.id + 1, scan["scan_id"])
        assert result2 is None
