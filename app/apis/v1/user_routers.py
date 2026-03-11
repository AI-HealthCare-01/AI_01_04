"""
사용자 라우터: 프로필 조회/수정, 이미지 업로드, 회원탈퇴
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.users import UserInfoResponse, UserUpdateRequest
from app.models.users import User
from app.services.users import UserManageService

user_router = APIRouter(prefix="/users", tags=["users"])


@user_router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def user_me_info(
    user: Annotated[User, Depends(get_request_user)],
) -> Response:
    return Response(UserInfoResponse.from_user(user).model_dump(), status_code=status.HTTP_200_OK)


@user_router.patch("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def update_user_me_info(
    update_data: UserUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    updated_user = await user_manage_service.update_user(user=user, data=update_data)
    return Response(UserInfoResponse.from_user(updated_user).model_dump(), status_code=status.HTTP_200_OK)


# 프로파일
@user_router.post("/me/profile-image", status_code=status.HTTP_200_OK)
async def upload_profile_image(
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
    file: Annotated[UploadFile, File()],
) -> Response:
    url = await user_manage_service.upload_profile_image(user=user, file=file)
    return Response({"profile_image_url": url}, status_code=status.HTTP_200_OK)


# 회원탈퇴(비활성화)
@user_router.delete("/me", status_code=status.HTTP_200_OK)
async def deactivate_me(
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    await user_manage_service.deactivate_user(user=user)
    return Response({"deleted": True}, status_code=status.HTTP_200_OK)
