from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.core import config

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


async def create_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """텍스트를 벡터 임베딩으로 변환"""
    client = get_openai_client()
    response = await client.embeddings.create(input=text, model=model)
    return response.data[0].embedding


async def chat_completion(system_prompt: str, user_prompt: str) -> str:
    """ChatCompletion 호출"""
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content or ""
