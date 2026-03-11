"""
텍스트 임베딩 서비스

- OpenAI text-embedding-3-small 모델로 1536차원 벡터 생성
- pgvector 유사도 검색에 사용
"""

from __future__ import annotations  # 프로젝트 가이드라인 - 모든 파일 최상단에 추가하는 forward reference 지원용

from openai import OpenAI

from app.core.config import Config

_client = OpenAI(api_key=Config().OPENAI_API_KEY)
_MODEL = "text-embedding-3-small"


def encode(text: str) -> list[float]:  # 텍스트를 받아서 숫자 배열을 반환하는 함수. 이게 "임베딩"
    response = _client.embeddings.create(input=text, model=_MODEL)
    return response.data[0].embedding
