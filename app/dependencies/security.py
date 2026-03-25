from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService

security = HTTPBearer()


async def get_request_user(
    request: Request,
    credential: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    """
    Authorization 헤더의 Bearer 토큰을 검증하여 현재 사용자 반환.

    Args:
        credential (HTTPAuthorizationCredentials): Bearer 토큰 자격증명.

    Returns:
        User: 인증된 활성 사용자 인스턴스.

    Raises:
        HTTPException: 토큰 유효하지 않거나 사용자가 존재하지 않으면 401.
        HTTPException: 비활성 사용자이면 401.
    """
    token = credential.credentials
    verified = JwtService().verify_jwt(token=token, token_type="access")
    user_id = verified.payload["user_id"]

    user = await UserRepository().get_user(user_id)
    if not user:
        raise HTTPException(detail="Authenticate Failed.", status_code=status.HTTP_401_UNAUTHORIZED)

    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(detail="Inactive user.", status_code=status.HTTP_401_UNAUTHORIZED)

    request.state.user_id = user.id
    return user
