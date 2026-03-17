from __future__ import annotations

from datetime import timedelta

import pytest

from app.utils.jwt.backends import TokenBackend
from app.utils.jwt.exceptions import TokenBackendError, TokenBackendExpiredError


@pytest.fixture
def backend() -> TokenBackend:
    return TokenBackend(algorithm="HS256", signing_key="test-secret")


class TestTokenBackend:
    """TokenBackend 테스트."""

    def test_invalid_algorithm_raises(self):
        """허용되지 않는 알고리즘 시 TokenBackendError 발생 확인."""
        with pytest.raises(TokenBackendError):
            TokenBackend(algorithm="RS256", signing_key="key")

    def test_encode_decode_roundtrip(self, backend):
        """인코딩 후 디코딩 시 원본 payload 복원 확인."""
        payload = {"user_id": 1, "exp": 9999999999}
        token = backend.encode(payload)
        decoded = backend.decode(token)
        assert decoded["user_id"] == 1

    def test_decode_invalid_token_raises(self, backend):
        """유효하지 않은 토큰 디코딩 시 TokenBackendError 발생 확인."""
        with pytest.raises(TokenBackendError):
            backend.decode("not.a.valid.token")

    def test_decode_expired_token_raises(self):
        """만료된 토큰 디코딩 시 TokenBackendExpiredError 발생 확인."""
        import time

        b = TokenBackend(algorithm="HS256", signing_key="test-secret")
        payload = {"user_id": 1, "exp": int(time.time()) - 10}
        token = b.encode(payload)
        with pytest.raises(TokenBackendExpiredError):
            b.decode(token)

    def test_get_leeway_none(self, backend):
        """leeway=None 시 timedelta(0) 반환 확인."""
        assert backend.get_leeway() == timedelta(seconds=0)

    def test_get_leeway_int(self):
        """leeway=int 시 timedelta(seconds=int) 반환 확인."""
        b = TokenBackend(algorithm="HS256", signing_key="key", leeway=30)
        assert b.get_leeway() == timedelta(seconds=30)

    def test_get_leeway_timedelta(self):
        """leeway=timedelta 시 그대로 반환 확인."""
        td = timedelta(minutes=5)
        b = TokenBackend(algorithm="HS256", signing_key="key", leeway=td)
        assert b.get_leeway() == td

    def test_get_leeway_invalid_raises(self):
        """leeway 타입 유효하지 않을 시 TokenBackendError 발생 확인."""
        b = TokenBackend(algorithm="HS256", signing_key="key", leeway="invalid")  # type: ignore
        with pytest.raises(TokenBackendError):
            b.get_leeway()

    def test_encode_with_audience(self):
        """audience 설정 시 aud 클레임 포함 확인."""
        b = TokenBackend(algorithm="HS256", signing_key="key", audience="myapp")
        payload = {"user_id": 1, "exp": 9999999999}
        token = b.encode(payload)
        decoded = b.decode(token)
        assert decoded["aud"] == "myapp"

    def test_encode_with_issuer(self):
        """issuer 설정 시 iss 클레임 포함 확인."""
        b = TokenBackend(algorithm="HS256", signing_key="key", issuer="myissuer")
        payload = {"user_id": 1, "exp": 9999999999}
        token = b.encode(payload)
        decoded = b.decode(token)
        assert decoded["iss"] == "myissuer"
