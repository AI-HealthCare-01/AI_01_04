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
    """
    로그인 사용자 프로필 조회.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.

    Returns:
        Response: UserInfoResponse 직렬화 데이터.
    """
    return Response(UserInfoResponse.from_user(user).model_dump(), status_code=status.HTTP_200_OK)


@user_router.patch("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def update_user_me_info(
    update_data: UserUpdateRequest,
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    """
    로그인 사용자 프로필 수정.

    Args:
        update_data (UserUpdateRequest): 수정할 필드 (name, email, phone_number, birthday, gender 등).
        user (User): JWT 인증으로 확인된 현재 사용자.
        user_manage_service (UserManageService): 사용자 관리 서비스 의존성.

    Returns:
        Response: 수정된 UserInfoResponse 데이터.

    Raises:
        HTTPException: 이메일/전화번호 중복 시 409.
    """
    updated_user = await user_manage_service.update_user(user=user, data=update_data)
    return Response(UserInfoResponse.from_user(updated_user).model_dump(), status_code=status.HTTP_200_OK)


# 프로파일
@user_router.post("/me/profile-image", status_code=status.HTTP_200_OK)
async def upload_profile_image(
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
    file: Annotated[UploadFile, File()],
) -> Response:
    """
    프로필 이미지 업로드.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        user_manage_service (UserManageService): 사용자 관리 서비스 의존성.
        file (UploadFile): 업로드할 이미지 파일 (jpg/png, 10MB 이하).

    Returns:
        Response: 저장된 profile_image_url 포함 응답.

    Raises:
        HTTPException: 파일 형식/용량 검증 실패 시 400.
    """
    url = await user_manage_service.upload_profile_image(user=user, file=file)
    return Response({"profile_image_url": url}, status_code=status.HTTP_200_OK)


# 회원탈퇴(비활성화)
@user_router.delete("/me", status_code=status.HTTP_200_OK)
async def deactivate_me(
    user: Annotated[User, Depends(get_request_user)],
    user_manage_service: Annotated[UserManageService, Depends(UserManageService)],
) -> Response:
    """
    회원 탈퇴 (소프트 마스크, is_active=False).

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        user_manage_service (UserManageService): 사용자 관리 서비스 의존성.

    Returns:
        Response: {"deleted": True} 응답.
    """
    await user_manage_service.deactivate_user(user=user)
    return Response({"deleted": True}, status_code=status.HTTP_200_OK)
