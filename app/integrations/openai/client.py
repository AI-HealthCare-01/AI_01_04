from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

from app.core import config

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """
    AsyncOpenAI 싱글턴 인스턴스 반환.

    Returns:
        AsyncOpenAI: 초기화된 AsyncOpenAI 클라이언트.
    """
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=15.0,
            max_retries=1,
        )
    return _client


async def create_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """
    텍스트를 벡터 임베딩으로 변환.

    Args:
        text (str): 임베딩할 텍스트.
        model (str): 사용할 임베딩 모델. 기본값 ``text-embedding-3-small``.

    Returns:
        list[float]: 임베딩 벡터.
    """
    client = get_openai_client()
    response = await client.embeddings.create(input=text, model=model)
    return response.data[0].embedding


async def chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> str:
    """
    ChatCompletion API 호출.

    Args:
        system_prompt (str): 시스템 프롬프트.
        user_prompt (str): 사용자 프롬프트.
        temperature (float): 생성 다양성 제어값.
        max_tokens (int | None): 최대 출력 토큰 수. None이면 모델 기본값 사용.

    Returns:
        str: 모델 응답 텍스트.
    """
    client = get_openai_client()
    kwargs: dict[str, Any] = {
        "model": config.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""
