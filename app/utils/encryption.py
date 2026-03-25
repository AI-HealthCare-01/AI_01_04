"""의료 데이터 필드 암호화/복호화 유틸리티.

Fernet 대칭키 암호화를 사용하여 진단명, 약물명, 대화 요약 등을 암호화 저장한다.
SECRET_KEY에서 Fernet 키를 파생한다.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core import config

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = hashlib.sha256(config.SECRET_KEY.encode()).digest()
        _fernet = Fernet(base64.urlsafe_b64encode(key))
    return _fernet


def encrypt(plain: str) -> str:
    if not plain:
        return plain
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    if not token:
        return token
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except Exception:
        return token  # 암호화 이전 데이터 호환
