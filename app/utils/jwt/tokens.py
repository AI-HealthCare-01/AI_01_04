from calendar import timegm
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Self
from uuid import uuid4

from app.core import config
from app.models.users import User
from app.utils.jwt.exceptions import ExpiredTokenError, TokenBackendError, TokenBackendExpiredError, TokenError
from app.utils.jwt.state import token_backend

if TYPE_CHECKING:
    from app.utils.jwt.backends import TokenBackend


class Token:
    """
    JWT 토큰 기본 클래스.

    AccessToken, RefreshToken의 공통 로직(인코딩/디코딩, exp/jti 설정)을 담당.
    직접 인스턴스화하지 않고 서브클래스를 사용해야 함.
    """

    token_type: str | None = None
    lifetime: timedelta | None = None
    _token_backend: "TokenBackend" = token_backend

    def __init__(self, token: str | None = None, verify: bool = True) -> None:
        if not self.token_type:
            raise TokenError("token_type must be set")
        if not self.lifetime:
            raise TokenError("lifetime must be set")

        self.token = token
        self.current_time = datetime.now(tz=config.TIMEZONE)
        self.payload: dict[str, Any] = {}

        if token is not None:
            try:
                self.payload = token_backend.decode(token, verify=verify)
            except TokenBackendExpiredError as err:
                raise ExpiredTokenError("Token is expired") from err
            except TokenBackendError as err:
                raise TokenError("Token is invalid") from err
        else:
            self.payload = {"type": self.token_type}
            self.set_exp(from_time=self.current_time, lifetime=self.lifetime)
            self.set_jti()

    def __repr__(self) -> str:
        return repr(self.payload)

    def __getitem__(self, key: str):
        return self.payload[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.payload[key] = value

    def __delitem__(self, key: str) -> None:
        del self.payload[key]

    def __contains__(self, key: str) -> Any:
        return key in self.payload

    def __str__(self) -> str:
        """
        Signs and returns a token as a base64 encoded string.
        """
        return self._token_backend.encode(self.payload)

    def set_exp(self, from_time: datetime | None = None, lifetime: timedelta | None = None) -> None:
        """
        토큰 만료 시각(exp) 설정.

        Args:
            from_time (datetime | None): 기준 시각. None이면 current_time 사용.
            lifetime (timedelta | None): 유효 기간. None이면 클래스 lifetime 사용.
        """
        if from_time is None:
            from_time = self.current_time

        if lifetime is None:
            lifetime = self.lifetime

        assert lifetime is not None

        dt = from_time + lifetime
        self.payload["exp"] = timegm(dt.timetuple())

    def set_jti(self) -> None:
        """토큰 고유 식별자(jti) UUID로 설정."""
        self.payload["jti"] = uuid4().hex

    @classmethod
    def for_user(cls, user: User) -> Self:
        """
        사용자 정보를 포함한 토큰 생성.

        Args:
            user (User): 토큰에 담을 사용자 인스턴스.

        Returns:
            Self: user_id가 포함된 토큰 인스턴스.
        """
        token = cls()
        token["user_id"] = user.id
        return token


class AccessToken(Token):
    """액세스 토큰. 짧은 유효 기간으로 API 인증에 사용."""

    token_type = "access"
    lifetime = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)


class RefreshToken(Token):
    """
    리프레시 토큰. 액세스 토큰 재발급에 사용.

    Attributes:
        no_copy_claims: 액세스 토큰 생성 시 복사하지 않을 클레임 목록.
    """

    token_type = "refresh"
    lifetime = timedelta(minutes=config.REFRESH_TOKEN_EXPIRE_MINUTES)
    no_copy_claims = {"exp", "jti", "type"}

    @property
    def access_token(self) -> AccessToken:
        """
        리프레시 토큰에서 새 액세스 토큰 생성.

        Returns:
            AccessToken: 리프레시 토큰의 클레임을 복사한 새 액세스 토큰.
        """
        access = AccessToken()
        access.set_exp(from_time=self.current_time)

        no_copy = self.no_copy_claims
        for claim, value in self.payload.items():
            if claim in no_copy:
                continue
            access[claim] = value

        return access
