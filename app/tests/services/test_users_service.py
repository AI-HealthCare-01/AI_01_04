from __future__ import annotations

from tortoise.contrib.test import TestCase

from app.dtos.users import UserUpdateRequest
from app.models.users import User
from app.services.users import UserManageService


async def _make_user(email: str, phone: str = "01011112222") -> User:
    return await User.create(email=email, name="테스터", phone_number=phone, birthday="1990-01-01")


class TestUserManageService(TestCase):
    """사용자 관리 서비스 테스트."""

    async def test_update_name(self):
        """사용자 이름 수정 성공 확인."""
        user = await _make_user("usr_upd@example.com")
        service = UserManageService()
        updated = await service.update_user(user, UserUpdateRequest(name="변경됨"))
        assert updated.name == "변경됨"

    async def test_update_phone_number(self):
        """사용자 전화번호 수정 성공 확인."""
        user = await _make_user("usr_phone@example.com", "01011112222")
        service = UserManageService()
        updated = await service.update_user(user, UserUpdateRequest(phone_number="01099998888"))
        assert updated.phone_number == "01099998888"

    async def test_update_duplicate_email_raises(self):
        """중복 이메일로 수정 시 HTTPException 발생 확인."""
        from fastapi import HTTPException

        await _make_user("existing@example.com")
        user = await _make_user("usr_dup@example.com", "01022223333")
        service = UserManageService()
        with self.assertRaises(HTTPException):
            await service.update_user(user, UserUpdateRequest(email="existing@example.com"))

    async def test_deactivate_user(self):
        """회원 탈퇴 시 is_active=False 설정 확인."""
        user = await _make_user("usr_deact@example.com")
        service = UserManageService()
        await service.deactivate_user(user)
        refreshed = await User.get(id=user.id)
        assert refreshed.is_active is False

    async def test_upload_profile_image_success(self):
        """프로필 이미지 업로드 성공 시 /static/ URL 반환 확인."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from fastapi import UploadFile

        user = await _make_user("usr_img@example.com")
        service = UserManageService()

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "avatar.jpg"
        mock_file.file = MagicMock()
        mock_file.file.tell.return_value = 100
        mock_file.file.seek = MagicMock()
        mock_file.seek = AsyncMock()
        mock_file.read = AsyncMock(side_effect=[b"fake", b""])

        with (
            patch("app.services.users.validate_extension"),
            patch("app.services.users.validate_size", new=AsyncMock(return_value=100)),
            patch("app.services.users.build_storage_path", return_value=MagicMock(name="avatar.jpg")),
            patch("app.services.users.save_upload_file", new=AsyncMock()),
        ):
            url = await service.upload_profile_image(user, mock_file)
        assert url.startswith("/static/")

    async def test_upload_profile_image_no_filename(self):
        """파일명 없는 업로드 시 ValueError 발생 확인."""
        from unittest.mock import MagicMock

        from fastapi import UploadFile

        user = await _make_user("usr_nofile@example.com")
        service = UserManageService()
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = None

        with self.assertRaises(ValueError):
            await service.upload_profile_image(user, mock_file)
