"""
인증 라우터: 회원가입, 로그인, 토큰 갱신
"""

# 인증 전용 라우터 : signup, login, refresh

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.dtos.auth import LoginRequest, LoginResponse, SignUpRequest, TokenRefreshResponse
from app.services.auth import AuthService
from app.services.jwt import JwtService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignUpRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """
    신규 사용자 회원가입.

    Args:
        request (SignUpRequest): 이메일, 비밀번호, 이름, 성별, 생년월일, 전화번호.
        auth_service (AuthService): 인증 서비스 의존성.

    Returns:
        Response: 회원가입 완료 메시지 (201 Created).

    Raises:
        HTTPException: 이메일 또는 전화번호 중복 시 409.
    """
    await auth_service.signup(request)
    return Response(content={"detail": "회원가입이 성공적으로 완료되었습니다."}, status_code=status.HTTP_201_CREATED)


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    """
    이메일/비밀번호 로그인.

    Args:
        request (LoginRequest): 이메일, 비밀번호.
        auth_service (AuthService): 인증 서비스 의존성.

    Returns:
        Response: access_token 포함 응답, refresh_token은 HttpOnly 쿠키로 설정.

    Raises:
        HTTPException: 인증 실패 시 401.
    """
    user = await auth_service.authenticate(request)
    tokens = await auth_service.login(user)
    resp = Response(
        content=LoginResponse(access_token=str(tokens["access_token"])).model_dump(), status_code=status.HTTP_200_OK
    )
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=True if config.ENV == Env.PROD else False,
        domain=config.COOKIE_DOMAIN or None,
        expires=tokens["refresh_token"].payload["exp"],
    )
    return resp


@auth_router.get("/token/refresh", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK)
async def token_refresh(
    jwt_service: Annotated[JwtService, Depends(JwtService)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    """
    Refresh Token으로 새 Access Token 발급.

    Args:
        jwt_service (JwtService): JWT 서비스 의존성.
        refresh_token (str | None): HttpOnly 쿠키의 refresh_token.

    Returns:
        Response: 새 access_token 포함 응답.

    Raises:
        HTTPException: refresh_token 누락 시 401, 만료/유효하지 않은 토큰 시 401.
    """
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing.")
    access_token = jwt_service.refresh_jwt(refresh_token)
    return Response(
        content=TokenRefreshResponse(access_token=str(access_token)).model_dump(), status_code=status.HTTP_200_OK
    )
