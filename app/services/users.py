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
        if data.email:
            await self.auth_service.check_email_exists(data.email)

        if data.phone_number:
            normalized_phone_number = normalize_phone_number(data.phone_number)
            await self.auth_service.check_phone_number_exists(normalized_phone_number)
            data.phone_number = normalized_phone_number

        async with in_transaction():
            await self.repo.update_instance(user=user, data=data.model_dump(exclude_none=True))
            await user.refresh_from_db()

        return user

    async def upload_profile_image(self, user: User, file: UploadFile) -> str:
        if not file.filename:
            raise ValueError("filename is missing")  # 또는 HTTPException(400)로 처리해도 OK

        filename = file.filename  # 여기부터 filename은 str로 확정

        validate_extension(filename)
        await validate_size(file)

        base_dir = getattr(config, "FILE_STORAGE_DIR", "./artifacts")
        dest = build_storage_path(base_dir=base_dir, user_id=user.id, original_filename=filename)

        await save_upload_file(file, dest)

        url = f"/static/{dest.name}"
        await self.repo.update_instance(user=user, data={"profile_image_url": url})
        await user.refresh_from_db()
        return url

    async def deactivate_user(self, user: User) -> None:
        async with in_transaction():
            await self.repo.deactivate_user(user_id=user.id)
