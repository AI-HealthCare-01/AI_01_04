"""Redis 캐시 유틸리티.

추천 결과, 약물 검색, 대시보드 등 반복 호출을 캐싱하여 응답 시간을 단축한다.
Redis 연결 실패 시 캐시를 건너뛰고 원본 로직을 실행한다 (graceful degradation).
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core import config

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None
_redis_unavailable: bool = False

# TTL 설정 (초)
TTL_DRUG_SEARCH = 86400  # 약물 검색: 24시간 (마스터 데이터)
TTL_RECOMMENDATION = 1800  # 추천 결과: 30분
TTL_DASHBOARD = 30  # 대시보드: 30초 (자주 변경)


async def get_redis() -> aioredis.Redis | None:
    global _redis, _redis_unavailable
    if _redis_unavailable:
        return None
    if _redis is not None:
        return _redis
    try:
        _redis = aioredis.from_url(config.REDIS_URL, decode_responses=True)
        await _redis.ping()  # type: ignore[misc]
        logger.info("Redis connected: %s", config.REDIS_URL)
        return _redis
    except Exception:
        logger.warning("Redis unavailable, caching disabled")
        _redis_unavailable = True
        _redis = None
        return None


def _make_key(prefix: str, *parts: Any) -> str:
    raw = ":".join(str(p) for p in parts)
    h = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"cache:{prefix}:{h}"


async def cache_get(prefix: str, *parts: Any) -> Any | None:
    r = await get_redis()
    if not r:
        return None
    try:
        val = await r.get(_make_key(prefix, *parts))
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(prefix: str, *parts: Any, value: Any, ttl: int = 3600) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        await r.set(
            _make_key(prefix, *parts),
            json.dumps(value, ensure_ascii=False, default=str),
            ex=ttl,
        )
    except Exception:
        pass


async def cache_delete(prefix: str, *parts: Any) -> None:
    r = await get_redis()
    if not r:
        return
    try:
        await r.delete(_make_key(prefix, *parts))
    except Exception:
        pass


async def cache_delete_pattern(prefix: str) -> None:
    """prefix로 시작하는 모든 캐시 키를 삭제한다."""
    r = await get_redis()
    if not r:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = await r.scan(cursor, match=f"cache:{prefix}:*", count=100)
            if keys:
                await r.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        pass
