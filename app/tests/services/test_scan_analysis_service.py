from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from starlette import status
from tortoise.contrib.test import TestCase

from app.integrations.ocr.exceptions import (
    OCRAuthError,
    OCRBadRequestError,
    OCRRateLimitError,
    OCRServerError,
    OCRTimeoutError,
)
from app.models.users import User
from app.services.scan_analysis import ScanAnalysisService

FAKE_OCR_RAW = {"images": [{"fields": [{"inferText": "아스피린 30일분"}]}], "version": "V2"}
FAKE_AI_RESULT = {
    "document_date": "2024-01-01",
    "diagnosis": "고혈압",
    "drugs": ["아스피린"],
    "raw_text": "아스피린 30일분",
    "ocr_raw": FAKE_OCR_RAW,
}


async def _make_user(email: str = "scan_svc@example.com") -> User:
    return await User.create(email=email, name="스캔테스터", phone_number="01011112222")


class TestScanAnalysisService(TestCase):
    async def test_get_result_not_found(self):
        user = await _make_user()
        mock_user = MagicMock()
        mock_user.id = user.id
        service = ScanAnalysisService()

        from fastapi import HTTPException

        with self.assertRaises(HTTPException) as ctx:
            await service.get_result(mock_user, scan_id=9999)
        assert ctx.exception.status_code == status.HTTP_404_NOT_FOUND

    async def test_start_analysis_success(self):
        user = await _make_user("scan_ok@example.com")
        mock_user = MagicMock()
        mock_user.id = user.id
        service = ScanAnalysisService()
        scan = await service.scan_repo.create(user_id=user.id, file_path="storage/1/test.jpg")

        with (
            patch.object(service.ocr_client, "analyze_file", new=AsyncMock(return_value=FAKE_OCR_RAW)),
            patch("app.services.scan_analysis.ai_postprocess", return_value=FAKE_AI_RESULT),
        ):
            result = await service.start_analysis(mock_user, scan_id=scan["scan_id"])

        assert result["status"] == "done"

    async def test_start_analysis_ocr_timeout(self):
        user = await _make_user("scan_timeout@example.com")
        mock_user = MagicMock()
        mock_user.id = user.id
        service = ScanAnalysisService()
        scan = await service.scan_repo.create(user_id=user.id, file_path="storage/1/test.jpg")

        from fastapi import HTTPException

        with patch.object(service.ocr_client, "analyze_file", new=AsyncMock(side_effect=OCRTimeoutError())):
            with self.assertRaises(HTTPException) as ctx:
                await service.start_analysis(mock_user, scan_id=scan["scan_id"])
        assert ctx.exception.status_code == status.HTTP_504_GATEWAY_TIMEOUT

    async def test_start_analysis_ocr_rate_limit(self):
        user = await _make_user("scan_rate@example.com")
        mock_user = MagicMock()
        mock_user.id = user.id
        service = ScanAnalysisService()
        scan = await service.scan_repo.create(user_id=user.id, file_path="storage/1/test.jpg")

        from fastapi import HTTPException

        with patch.object(service.ocr_client, "analyze_file", new=AsyncMock(side_effect=OCRRateLimitError())):
            with self.assertRaises(HTTPException) as ctx:
                await service.start_analysis(mock_user, scan_id=scan["scan_id"])
        assert ctx.exception.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    async def test_start_analysis_ocr_auth_error(self):
        user = await _make_user("scan_auth@example.com")
        mock_user = MagicMock()
        mock_user.id = user.id
        service = ScanAnalysisService()
        scan = await service.scan_repo.create(user_id=user.id, file_path="storage/1/test.jpg")

        from fastapi import HTTPException

        with patch.object(service.ocr_client, "analyze_file", new=AsyncMock(side_effect=OCRAuthError())):
            with self.assertRaises(HTTPException) as ctx:
                await service.start_analysis(mock_user, scan_id=scan["scan_id"])
        assert ctx.exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    async def test_start_analysis_ocr_bad_request(self):
        user = await _make_user("scan_bad@example.com")
        mock_user = MagicMock()
        mock_user.id = user.id
        service = ScanAnalysisService()
        scan = await service.scan_repo.create(user_id=user.id, file_path="storage/1/test.jpg")

        from fastapi import HTTPException

        with patch.object(service.ocr_client, "analyze_file", new=AsyncMock(side_effect=OCRBadRequestError())):
            with self.assertRaises(HTTPException) as ctx:
                await service.start_analysis(mock_user, scan_id=scan["scan_id"])
        assert ctx.exception.status_code == status.HTTP_400_BAD_REQUEST

    async def test_start_analysis_ocr_server_error(self):
        user = await _make_user("scan_srv@example.com")
        mock_user = MagicMock()
        mock_user.id = user.id
        service = ScanAnalysisService()
        scan = await service.scan_repo.create(user_id=user.id, file_path="storage/1/test.jpg")

        from fastapi import HTTPException

        with patch.object(service.ocr_client, "analyze_file", new=AsyncMock(side_effect=OCRServerError())):
            with self.assertRaises(HTTPException) as ctx:
                await service.start_analysis(mock_user, scan_id=scan["scan_id"])
        assert ctx.exception.status_code == status.HTTP_502_BAD_GATEWAY

    async def test_update_result_not_found(self):
        from fastapi import HTTPException

        from app.dtos.scan import ScanResultUpdateRequest

        user = await _make_user("scan_upd@example.com")
        mock_user = MagicMock()
        mock_user.id = user.id
        service = ScanAnalysisService()

        with self.assertRaises(HTTPException) as ctx:
            await service.update_result(mock_user, scan_id=9999, data=ScanResultUpdateRequest(diagnosis="고혈압"))
        assert ctx.exception.status_code == status.HTTP_404_NOT_FOUND

    async def test_save_result_no_document_date(self):
        from fastapi import HTTPException

        user = await _make_user("scan_nodoc@example.com")
        mock_user = MagicMock()
        mock_user.id = user.id
        service = ScanAnalysisService()
        scan = await service.scan_repo.create(user_id=user.id, file_path="storage/1/test.jpg")

        with self.assertRaises(HTTPException) as ctx:
            await service.save_result(mock_user, scan_id=scan["scan_id"])
        assert ctx.exception.status_code == status.HTTP_400_BAD_REQUEST

    async def test_save_result_success(self):
        user = await _make_user("scan_save@example.com")
        mock_user = MagicMock()
        mock_user.id = user.id
        mock_user.pk = user.id
        service = ScanAnalysisService()
        scan = await service.scan_repo.create(user_id=user.id, file_path="storage/1/test.jpg")
        await service.scan_repo.update(
            user.id,
            scan["scan_id"],
            status="done",
            document_date="2024-01-01",
            diagnosis="고혈압",
            drugs=["아스피린"],
        )

        with (
            patch.object(service.med_service, "ensure_day_seed", new=AsyncMock(), create=True),
            patch.object(service.health_service, "ensure_day_seed", new=AsyncMock(), create=True),
        ):
            result = await service.save_result(user, scan_id=scan["scan_id"])
        assert result["saved"] is True

    async def test_save_result_idempotent_duplicate_skip(self):
        user = await _make_user("scan_idempotent@example.com")
        service = ScanAnalysisService()
        scan = await service.scan_repo.create(user_id=user.id, file_path="storage/1/test.jpg")
        await service.scan_repo.update(
            user.id,
            scan["scan_id"],
            status="done",
            document_date="2024-01-01",
            diagnosis="고혈압",
            drugs=["아스피린", "타이레놀"],
        )

        with (
            patch.object(service.med_service, "ensure_day_seed", new=AsyncMock(), create=True),
            patch.object(service.health_service, "ensure_day_seed", new=AsyncMock(), create=True),
        ):
            first = await service.save_result(user, scan_id=scan["scan_id"])
            second = await service.save_result(user, scan_id=scan["scan_id"])

        assert first["saved"] is True
        assert len(first["created_prescriptions"]) == 2
        assert first["skipped_count"] == 0

        assert second["saved"] is True
        assert len(second["created_prescriptions"]) == 0
        assert second["skipped_count"] == 2
        assert set(second["skipped_duplicates"]) == {"아스피린", "타이레놀"}
