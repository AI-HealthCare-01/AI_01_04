from __future__ import annotations

from tortoise.contrib.test import TestCase

from app.repositories.scan_repository import ScanRepository


class TestScanRepository(TestCase):
    async def test_create_and_get_scan(self):
        """스캔 생성 및 조회"""
        repo = ScanRepository()
        scan = await repo.create(user_id=1, file_path="test.jpg")

        assert scan["scan_id"] is not None
        assert scan["user_id"] == 1
        assert scan["status"] == "uploaded"

        # 조회 (같은 user_id면 조회 가능)
        result = await repo.get_by_id_for_user(1, scan["scan_id"])
        assert result is not None
        assert result["scan_id"] == scan["scan_id"]

        # 다른 사용자는 조회 불가
        result2 = await repo.get_by_id_for_user(2, scan["scan_id"])
        assert result2 is None
