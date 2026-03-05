from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from app.services.jwt import JwtService
from app.utils.jwt.exceptions import ExpiredTokenError, TokenError
from app.utils.jwt.tokens import AccessToken, RefreshToken, Token


class TestToken:
    def test_token_type_not_set_raises(self):
        class BadToken(Token):
            token_type = None
            lifetime = None

        with pytest.raises(TokenError):
            BadToken()

    def test_getitem_setitem(self):
        t = AccessToken()
        t["custom"] = "value"
        assert t["custom"] == "value"

    def test_delitem(self):
        t = AccessToken()
        t["custom"] = "value"
        del t["custom"]
        assert "custom" not in t

    def test_contains(self):
        t = AccessToken()
        assert "type" in t

    def test_repr(self):
        t = AccessToken()
        assert "access" in repr(t)

    def test_str_returns_encoded_token(self):
        t = AccessToken()
        token_str = str(t)
        assert isinstance(token_str, str)
        assert len(token_str) > 0

    def test_for_user(self):
        user = MagicMock()
        user.id = 42
        t = AccessToken.for_user(user)
        assert t["user_id"] == 42

    def test_decode_valid_token(self):
        t = AccessToken()
        token_str = str(t)
        decoded = AccessToken(token=token_str)
        assert decoded["type"] == "access"

    def test_decode_expired_token_raises(self):
        from app.utils.jwt.state import token_backend

        payload = {"type": "access", "exp": int(time.time()) - 10, "jti": "abc"}
        expired_token = token_backend.encode(payload)

        with pytest.raises(ExpiredTokenError):
            AccessToken(token=expired_token)

    def test_decode_invalid_token_raises(self):
        with pytest.raises(TokenError):
            AccessToken(token="invalid.token.here")

    def test_refresh_token_access_token_property(self):
        user = MagicMock()
        user.id = 1
        rt = RefreshToken.for_user(user)
        at = rt.access_token
        assert at["type"] == "access"
        assert at["user_id"] == 1

    def test_set_exp(self):
        from datetime import timedelta

        t = AccessToken()
        t.set_exp(lifetime=timedelta(hours=1))
        assert "exp" in t.payload

    def test_set_jti(self):
        t = AccessToken()
        t.set_jti()
        assert "jti" in t.payload


class TestJwtService:
    def test_create_access_token(self):
        user = MagicMock()
        user.id = 1
        service = JwtService()
        at = service.create_access_token(user)
        assert at["user_id"] == 1

    def test_create_refresh_token(self):
        user = MagicMock()
        user.id = 1
        service = JwtService()
        rt = service.create_refresh_token(user)
        assert rt["user_id"] == 1

    def test_verify_jwt_access_valid(self):
        user = MagicMock()
        user.id = 1
        service = JwtService()
        at = service.create_access_token(user)
        verified = service.verify_jwt(str(at), token_type="access")
        assert verified["user_id"] == 1

    def test_verify_jwt_expired_raises_401(self):
        from fastapi import HTTPException

        from app.utils.jwt.state import token_backend

        payload = {"type": "access", "exp": int(time.time()) - 10, "jti": "abc"}
        expired = token_backend.encode(payload)

        service = JwtService()
        with pytest.raises(HTTPException) as ctx:
            service.verify_jwt(expired, token_type="access")
        assert ctx.value.status_code == 401

    def test_verify_jwt_invalid_raises_400(self):
        from fastapi import HTTPException

        service = JwtService()
        with pytest.raises(HTTPException) as ctx:
            service.verify_jwt("bad.token", token_type="access")
        assert ctx.value.status_code == 400

    def test_refresh_jwt(self):
        user = MagicMock()
        user.id = 1
        service = JwtService()
        rt = service.create_refresh_token(user)
        at = service.refresh_jwt(str(rt))
        assert at["user_id"] == 1

    def test_issue_jwt_pair(self):
        user = MagicMock()
        user.id = 1
        service = JwtService()
        pair = service.issue_jwt_pair(user)
        assert "access_token" in pair
        assert "refresh_token" in pair
