from __future__ import annotations

from datetime import timedelta

import pytest

from app.utils.jwt.backends import TokenBackend
from app.utils.jwt.exceptions import TokenBackendError, TokenBackendExpiredError


@pytest.fixture
def backend() -> TokenBackend:
    return TokenBackend(algorithm="HS256", signing_key="test-secret")


class TestTokenBackend:
    def test_invalid_algorithm_raises(self):
        with pytest.raises(TokenBackendError):
            TokenBackend(algorithm="RS256", signing_key="key")

    def test_encode_decode_roundtrip(self, backend):
        payload = {"user_id": 1, "exp": 9999999999}
        token = backend.encode(payload)
        decoded = backend.decode(token)
        assert decoded["user_id"] == 1

    def test_decode_invalid_token_raises(self, backend):
        with pytest.raises(TokenBackendError):
            backend.decode("not.a.valid.token")

    def test_decode_expired_token_raises(self):
        import time

        b = TokenBackend(algorithm="HS256", signing_key="test-secret")
        payload = {"user_id": 1, "exp": int(time.time()) - 10}
        token = b.encode(payload)
        with pytest.raises(TokenBackendExpiredError):
            b.decode(token)

    def test_get_leeway_none(self, backend):
        assert backend.get_leeway() == timedelta(seconds=0)

    def test_get_leeway_int(self):
        b = TokenBackend(algorithm="HS256", signing_key="key", leeway=30)
        assert b.get_leeway() == timedelta(seconds=30)

    def test_get_leeway_timedelta(self):
        td = timedelta(minutes=5)
        b = TokenBackend(algorithm="HS256", signing_key="key", leeway=td)
        assert b.get_leeway() == td

    def test_get_leeway_invalid_raises(self):
        b = TokenBackend(algorithm="HS256", signing_key="key", leeway="invalid")  # type: ignore
        with pytest.raises(TokenBackendError):
            b.get_leeway()

    def test_encode_with_audience(self):
        b = TokenBackend(algorithm="HS256", signing_key="key", audience="myapp")
        payload = {"user_id": 1, "exp": 9999999999}
        token = b.encode(payload)
        decoded = b.decode(token)
        assert decoded["aud"] == "myapp"

    def test_encode_with_issuer(self):
        b = TokenBackend(algorithm="HS256", signing_key="key", issuer="myissuer")
        payload = {"user_id": 1, "exp": 9999999999}
        token = b.encode(payload)
        decoded = b.decode(token)
        assert decoded["iss"] == "myissuer"
