from __future__ import annotations

import pytest

from app.integrations.ocr.parser import extract_document_date, extract_full_text, parse_ocr_result
from app.utils.common import normalize_phone_number
from app.utils.files import FileValidationError, sanitize_filename, validate_extension


class TestNormalizePhoneNumber:
    def test_international_format(self):
        assert normalize_phone_number("+821012345678") == "01012345678"

    def test_with_dashes(self):
        assert normalize_phone_number("010-1234-5678") == "01012345678"

    def test_plain(self):
        assert normalize_phone_number("01012345678") == "01012345678"


class TestSanitizeFilename:
    def test_normal(self):
        assert sanitize_filename("test.jpg") == "test.jpg"

    def test_path_traversal(self):
        result = sanitize_filename("../../etc/passwd")
        assert "/" not in result
        assert ".." not in result

    def test_special_chars(self):
        result = sanitize_filename("파일 이름!@#.jpg")
        assert " " not in result

    def test_empty_becomes_uuid(self):
        result = sanitize_filename("")
        assert result.startswith("file_")

    def test_dot_becomes_uuid(self):
        result = sanitize_filename(".")
        assert result.startswith("file_")


class TestValidateExtension:
    def test_valid_jpg(self):
        validate_extension("photo.jpg")  # 예외 없음

    def test_valid_pdf(self):
        validate_extension("doc.pdf")

    def test_invalid_raises(self):
        with pytest.raises(FileValidationError):
            validate_extension("script.exe")

    def test_custom_allowed(self):
        validate_extension("data.csv", allowed={".csv"})

    def test_custom_not_allowed_raises(self):
        with pytest.raises(FileValidationError):
            validate_extension("photo.jpg", allowed={".png"})


class TestValidateSize:
    @pytest.mark.asyncio
    async def test_seek_tell_fallback(self):
        """seek/tell 실패 시 chunk 읽기 fallback 경로"""
        from unittest.mock import AsyncMock, MagicMock

        from fastapi import UploadFile

        mock = MagicMock(spec=UploadFile)
        mock.file = MagicMock()
        mock.file.tell.side_effect = OSError("not seekable")
        mock.seek = AsyncMock()
        mock.read = AsyncMock(side_effect=[b"x" * 100, b""])

        from app.utils.files import validate_size

        size = await validate_size(mock, max_bytes=10 * 1024 * 1024)
        assert size == 100

    @pytest.mark.asyncio
    async def test_fallback_exceeds_max(self):
        """fallback 경로에서 max_bytes 초과 시 에러"""
        from unittest.mock import AsyncMock, MagicMock

        from fastapi import UploadFile

        mock = MagicMock(spec=UploadFile)
        mock.file = MagicMock()
        mock.file.tell.side_effect = OSError("not seekable")
        mock.seek = AsyncMock()
        mock.read = AsyncMock(side_effect=[b"x" * 200, b""])

        from app.utils.files import validate_size

        with pytest.raises(FileValidationError):
            await validate_size(mock, max_bytes=100)


class TestSaveUserUploadFile:
    @pytest.mark.asyncio
    async def test_no_filename_raises(self):
        from unittest.mock import MagicMock

        from fastapi import UploadFile

        from app.utils.files import save_user_upload_file

        mock = MagicMock(spec=UploadFile)
        mock.filename = None

        with pytest.raises(FileValidationError):
            await save_user_upload_file(user_id=1, upload=mock)


class TestOCRParser:
    def test_extract_full_text_fields(self):
        raw = {"images": [{"fields": [{"inferText": "아스피린"}, {"inferText": "30일"}]}]}
        text = extract_full_text(raw)
        assert "아스피린" in text
        assert "30일" in text

    def test_extract_full_text_lines(self):
        raw = {"images": [{"lines": [{"text": "처방전"}]}]}
        text = extract_full_text(raw)
        assert "처방전" in text

    def test_extract_full_text_parsed_text(self):
        raw = {"images": [{"parsedText": "진단명: 고혈압"}]}
        text = extract_full_text(raw)
        assert "고혈압" in text

    def test_extract_full_text_infer_text(self):
        raw = {"images": [{"inferText": "약품명"}]}
        text = extract_full_text(raw)
        assert "약품명" in text

    def test_extract_full_text_empty(self):
        assert extract_full_text({}) == ""

    def test_extract_document_date_found(self):
        assert extract_document_date("처방일: 2024.01.15") == "2024-01-15"

    def test_extract_document_date_not_found(self):
        assert extract_document_date("날짜 없음") is None

    def test_parse_ocr_result(self):
        raw = {"images": [{"fields": [{"inferText": "2024.03.01 아스피린"}]}]}
        result = parse_ocr_result(raw)
        assert result["document_date"] == "2024-03-01"
        assert result["raw_text"] is not None
        assert result["ocr_raw"] is raw

    def test_parse_ocr_result_empty(self):
        result = parse_ocr_result({})
        assert result["document_date"] is None
        assert result["raw_text"] is None
