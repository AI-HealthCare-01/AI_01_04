from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from app.services.jwt import JwtService
from app.utils.jwt.exceptions import ExpiredTokenError, TokenError
from app.utils.jwt.tokens import AccessToken, RefreshToken, Token


class TestToken:
    """Token 및 AccessToken/RefreshToken 테스트."""

    def test_token_type_not_set_raises(self):
        """token_type 미설정 시 TokenError 발생 확인."""

        class BadToken(Token):
            token_type = None
            lifetime = None

        with pytest.raises(TokenError):
            BadToken()

    def test_getitem_setitem(self):
        """payload 항목 설정/조회 확인."""
        t = AccessToken()
        t["custom"] = "value"
        assert t["custom"] == "value"

    def test_delitem(self):
        """payload 항목 삭제 확인."""
        t = AccessToken()
        t["custom"] = "value"
        del t["custom"]
        assert "custom" not in t

    def test_contains(self):
        """payload 항목 포함 여부 확인."""
        t = AccessToken()
        assert "type" in t

    def test_repr(self):
        """repr에 token_type 포함 확인."""
        t = AccessToken()
        assert "access" in repr(t)

    def test_str_returns_encoded_token(self):
        """str() 호출 시 인코딩된 JWT 문자열 반환 확인."""
        t = AccessToken()
        token_str = str(t)
        assert isinstance(token_str, str)
        assert len(token_str) > 0

    def test_for_user(self):
        """for_user 시 user_id 클레임 포함 확인."""
        user = MagicMock()
        user.id = 42
        t = AccessToken.for_user(user)
        assert t["user_id"] == 42

    def test_decode_valid_token(self):
        """유효한 토큰 디코딩 시 type=access 확인."""
        t = AccessToken()
        token_str = str(t)
        decoded = AccessToken(token=token_str)
        assert decoded["type"] == "access"

    def test_decode_expired_token_raises(self):
        """만료된 토큰 디코딩 시 ExpiredTokenError 발생 확인."""
        from app.utils.jwt.state import token_backend

        payload = {"type": "access", "exp": int(time.time()) - 10, "jti": "abc"}
        expired_token = token_backend.encode(payload)

        with pytest.raises(ExpiredTokenError):
            AccessToken(token=expired_token)

    def test_decode_invalid_token_raises(self):
        """유효하지 않은 토큰 디코딩 시 TokenError 발생 확인."""
        with pytest.raises(TokenError):
            AccessToken(token="invalid.token.here")

    def test_refresh_token_access_token_property(self):
        """RefreshToken.access_token 프로퍼티로 AccessToken 생성 확인."""
        user = MagicMock()
        user.id = 1
        rt = RefreshToken.for_user(user)
        at = rt.access_token
        assert at["type"] == "access"
        assert at["user_id"] == 1

    def test_set_exp(self):
        """set_exp 호출 시 exp 클레임 설정 확인."""
        from datetime import timedelta

        t = AccessToken()
        t.set_exp(lifetime=timedelta(hours=1))
        assert "exp" in t.payload

    def test_set_jti(self):
        """set_jti 호출 시 jti 클레임 설정 확인."""
        t = AccessToken()
        t.set_jti()
        assert "jti" in t.payload


class TestJwtService:
    """JwtService 테스트."""

    def test_create_access_token(self):
        """access token 생성 시 user_id 클레임 포함 확인."""
        user = MagicMock()
        user.id = 1
        service = JwtService()
        at = service.create_access_token(user)
        assert at["user_id"] == 1

    def test_create_refresh_token(self):
        """refresh token 생성 시 user_id 클레임 포함 확인."""
        user = MagicMock()
        user.id = 1
        service = JwtService()
        rt = service.create_refresh_token(user)
        assert rt["user_id"] == 1

    def test_verify_jwt_access_valid(self):
        """유효한 access token 검증 성공 확인."""
        user = MagicMock()
        user.id = 1
        service = JwtService()
        at = service.create_access_token(user)
        verified = service.verify_jwt(str(at), token_type="access")
        assert verified["user_id"] == 1

    def test_verify_jwt_expired_raises_401(self):
        """만료된 토큰 검증 시 401 발생 확인."""
        from fastapi import HTTPException

        from app.utils.jwt.state import token_backend

        payload = {"type": "access", "exp": int(time.time()) - 10, "jti": "abc"}
        expired = token_backend.encode(payload)

        service = JwtService()
        with pytest.raises(HTTPException) as ctx:
            service.verify_jwt(expired, token_type="access")
        assert ctx.value.status_code == 401

    def test_verify_jwt_invalid_raises_400(self):
        """유효하지 않은 토큰 검증 시 400 발생 확인."""
        from fastapi import HTTPException

        service = JwtService()
        with pytest.raises(HTTPException) as ctx:
            service.verify_jwt("bad.token", token_type="access")
        assert ctx.value.status_code == 400

    def test_refresh_jwt(self):
        """refresh token으로 새 access token 발급 확인."""
        user = MagicMock()
        user.id = 1
        service = JwtService()
        rt = service.create_refresh_token(user)
        at = service.refresh_jwt(str(rt))
        assert at["user_id"] == 1

    def test_issue_jwt_pair(self):
        """access/refresh token 쌍 발급 확인."""
        user = MagicMock()
        user.id = 1
        service = JwtService()
        pair = service.issue_jwt_pair(user)
        assert "access_token" in pair
        assert "refresh_token" in pair
