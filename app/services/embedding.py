"""텍스트 임베딩 서비스.

OpenAI text-embedding-3-small 모델로 1536차원 벡터를 생성한다.
생성된 벡터는 pgvector 유사도 검색에 사용된다.
"""

from __future__ import annotations

from openai import OpenAI

from app.core.config import Config

_client = OpenAI(api_key=Config().OPENAI_API_KEY)
_MODEL = "text-embedding-3-small"


def encode(text: str) -> list[float]:
    """텍스트를 1536차원 임베딩 벡터로 변환한다.

    Args:
        text (str): 임베딩할 텍스트.

    Returns:
        list[float]: 1536차원 부동소수점 벡터.
    """
    response = _client.embeddings.create(input=text, model=_MODEL)
    return response.data[0].embedding


def encode_batch(texts: list[str]) -> list[list[float]]:
    """텍스트 목록을 한 번의 API 호출로 일괄 임베딩한다.

    Args:
        texts (list[str]): 임베딩할 텍스트 목록.

    Returns:
        list[list[float]]: 각 텍스트에 대한 1536차원 벡터 목록.
    """
    response = _client.embeddings.create(input=texts, model=_MODEL)
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
