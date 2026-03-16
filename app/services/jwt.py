"""JWT 서비스.

Access/Refresh 토큰 생성, 검증, 갱신을 담당한다.
토큰 만료/유효하지 않은 토큰은 HTTPException으로 변환한다.
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
        """사용자의 Access 토큰을 생성한다.

        Args:
            user (User): 토큰을 생성할 User 객체.

        Returns:
            AccessToken: 생성된 AccessToken 객체.
        """
        return self.access_token_class.for_user(user)

    def create_refresh_token(self, user: User) -> RefreshToken:
        """사용자의 Refresh 토큰을 생성한다.

        Args:
            user (User): 토큰을 생성할 User 객체.

        Returns:
            RefreshToken: 생성된 RefreshToken 객체.
        """
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
        """JWT 토큰을 검증한다.

        Args:
            token (str): 검증할 JWT 토큰 문자열.
            token_type (Literal["access", "refresh"]): 토큰 유형.

        Returns:
            AccessToken | RefreshToken: 검증된 토큰 객체.

        Raises:
            HTTPException: 토큰 만료(401), 유효하지 않은 토큰(400) 시.
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
        """Refresh 토큰으로 새 Access 토큰을 발급한다.

        Args:
            refresh_token (str): 유효한 Refresh 토큰 문자열.

        Returns:
            AccessToken: 새로 발급된 AccessToken 객체.

        Raises:
            HTTPException: 토큰 만료(401), 유효하지 않은 토큰(400) 시.
        """
        verified_rt = self.verify_jwt(token=refresh_token, token_type="refresh")
        return verified_rt.access_token

    def issue_jwt_pair(self, user: User) -> dict[str, AccessToken | RefreshToken]:
        """Access/Refresh 토큰 쌍을 생성하여 반환한다.

        Args:
            user (User): 토큰을 발급할 User 객체.

        Returns:
            dict[str, AccessToken | RefreshToken]: access_token과 refresh_token이 담긴 딕셔너리.
        """
        rt = self.create_refresh_token(user)
        at = rt.access_token
        return {"access_token": at, "refresh_token": rt}
