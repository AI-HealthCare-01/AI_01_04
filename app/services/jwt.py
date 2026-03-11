"""
JWT 서비스

- Access/Refresh 토큰 생성, 검증, 갱신 담당
- 토큰 만료/유효하지 않은 토큰은 HTTPException으로 변환
"""

from typing import Literal, overload

from fastapi import HTTPException

from app.models.users import User
from app.utils.jwt.exceptions import ExpiredTokenError, TokenError
from app.utils.jwt.tokens import AccessToken, RefreshToken


class JwtService:
    access_token_class = AccessToken
    refresh_token_class = RefreshToken

    def create_access_token(self, user: User) -> AccessToken:
        """사용자의 Access 토큰 생성"""
        return self.access_token_class.for_user(user)

    def create_refresh_token(self, user: User) -> RefreshToken:
        """사용자의 Refresh 토큰 생성"""
        return self.refresh_token_class.for_user(user)

    @overload
    def verify_jwt(
        self,
        token: str,
        token_type: Literal["access"],
    ) -> AccessToken: ...

    @overload
    def verify_jwt(
        self,
        token: str,
        token_type: Literal["refresh"],
    ) -> RefreshToken: ...

    def verify_jwt(self, token: str, token_type: Literal["access", "refresh"]) -> AccessToken | RefreshToken:
        """
        JWT 토큰 검증

        - 만료 시 401, 유효하지 않은 토큰 시 400 예외 발생
        """
        token_class: type[AccessToken | RefreshToken]
        if token_type == "access":
            token_class = self.access_token_class
        else:
            token_class = self.refresh_token_class

        try:
            verified = token_class(token=token)
            return verified
        except ExpiredTokenError as err:
            raise HTTPException(status_code=401, detail=f"{token_type} token has expired.") from err
        except TokenError as err:
            raise HTTPException(status_code=400, detail="Provided invalid token.") from err

    def refresh_jwt(self, refresh_token: str) -> AccessToken:
        """Refresh 토큰으로 새 Access 토큰 발급"""
        verified_rt = self.verify_jwt(token=refresh_token, token_type="refresh")
        return verified_rt.access_token

    def issue_jwt_pair(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        """Access/Refresh 토큰 쌍 생성 및 반환"""
        rt = self.create_refresh_token(user)
        at = rt.access_token
        return {"access_token": at, "refresh_token": rt}
