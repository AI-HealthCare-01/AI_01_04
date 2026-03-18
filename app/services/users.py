"""사용자 관리 서비스.

프로필 수정, 프로필 이미지 업로드, 회원 탈퇴(비활성화)를 담당한다.
"""

from __future__ import annotations

from fastapi import UploadFile
from tortoise.transactions import in_transaction

from app.core import config
from app.dtos.users import UserUpdateRequest
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.auth import AuthService
from app.utils.common import normalize_phone_number
from app.utils.files import build_storage_path, save_upload_file, validate_extension, validate_size


class UserManageService:
    def __init__(self):
        self.repo = UserRepository()
        self.auth_service = AuthService()

    async def update_user(self, user: User, data: UserUpdateRequest) -> User:
        """사용자 정보를 수정한다.

        이메일/전화번호 변경 시 중복 검증을 선행하며,
        전화번호는 정규화 후 저장한다.

        Args:
            user (User): 수정할 User 객체.
            data (UserUpdateRequest): 수정할 필드가 담긴 요청 데이터.

        Returns:
            User: 업데이트된 User 객체.

        Raises:
            HTTPException: 이메일 중복(409), 전화번호 중복(409) 시.
        """
        if data.email:
            await self.auth_service.check_email_exists(data.email)

        if data.phone_number:
            normalized_phone_number = normalize_phone_number(data.phone_number)
            await self.auth_service.check_phone_number_exists(normalized_phone_number)
            data.phone_number = normalized_phone_number

        update_data = data.model_dump(exclude_none=True)

        async with in_transaction():
            await self.repo.update_instance(user=user, data=update_data)
            await user.refresh_from_db()

        return user

    async def upload_profile_image(self, user: User, file: UploadFile) -> str:
        """프로필 이미지를 업로드한다.

        확장자/용량 검증 후 저장하며, 저장 경로를 /static/ URL로 변환하여 반환한다.

        Args:
            user (User): 이미지를 업로드할 User 객체.
            file (UploadFile): 업로드할 이미지 파일.

        Returns:
            str: 저장된 이미지의 /static/ URL.

        Raises:
            ValueError: 파일명이 없을 시.
            HTTPException: 허용되지 않는 확장자 또는 용량 초과 시.
        """
        if not file.filename:
            raise ValueError("filename is missing")

        filename = file.filename

        validate_extension(filename)
        await validate_size(file)

        base_dir = config.FILE_STORAGE_DIR
        dest = build_storage_path(base_dir=base_dir, user_id=user.id, original_filename=filename)

        await save_upload_file(file, dest)

        url = f"/static/{dest.name}"
        await self.repo.update_instance(user=user, data={"profile_image_url": url})
        await user.refresh_from_db()
        return url

    async def deactivate_user(self, user: User) -> None:
        """회원을 탈퇴 처리한다 (is_active=False, 실제 삭제 없음).

        Args:
            user (User): 탈퇴 처리할 User 객체.
        """
        async with in_transaction():
            await self.repo.deactivate_user(user_id=user.id)
