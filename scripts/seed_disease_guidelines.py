"""
질병 가이드라인 임베딩 seed 스크립트.

disease_guidelines 테이블 → vector_documents 임베딩 생성
(OpenAI text-embedding-3-small, 1536차원).

실행:
    uv run python scripts/seed_disease_guidelines.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

import tiktoken
from openai import RateLimitError
from tortoise import Tortoise

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.databases import TORTOISE_ORM
from app.models.diseases import DiseaseGuideline
from app.models.vector_documents import VectorDocument
from app.services.embedding import encode_batch

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

REFERENCE_TYPE = "disease_guideline"
MAX_TOKENS_PER_REQUEST = 250_000
MAX_TOKENS_PER_TEXT = 8000

_tokenizer = tiktoken.get_encoding("cl100k_base")


def _truncate_to_tokens(text: str) -> str:
    tokens = _tokenizer.encode(text)
    if len(tokens) <= MAX_TOKENS_PER_TEXT:
        return text
    return _tokenizer.decode(tokens[:MAX_TOKENS_PER_TEXT])


def _make_batches(texts: list[str]) -> list[list[str]]:
    """토큰 수 기준으로 텍스트를 동적 배치로 분할한다."""
    batches: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0
    for text in texts:
        token_count = len(_tokenizer.encode(text))
        if current and current_tokens + token_count > MAX_TOKENS_PER_REQUEST:
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(text)
        current_tokens += token_count
    if current:
        batches.append(current)
    return batches


async def seed() -> None:
    await Tortoise.init(config=TORTOISE_ORM)

    # disease_guidelines + disease 이름 함께 조회
    guidelines = await DiseaseGuideline.all().select_related("disease")
    total = len(guidelines)
    logger.info("총 %d건 처리 시작", total)

    # 이미 임베딩된 id 조회 — 재실행 시 스킵
    done_ids = set(await VectorDocument.filter(reference_type=REFERENCE_TYPE).values_list("reference_id", flat=True))
    logger.info("이미 완료된 임베딩: %d건 스킵", len(done_ids))

    # 임베딩 텍스트 구성
    all_texts = [
        _truncate_to_tokens(
            f"질병명: {g.disease.name}\n"
            f"질병코드(KCD): {g.disease.kcd_code or '없음'}\n"
            f"카테고리: {g.category}\n"
            f"내용: {g.content}"
        )
        for g in guidelines
    ]

    batches = _make_batches(all_texts)
    logger.info("임베딩 배치 수: %d", len(batches))

    processed = 0
    for batch_texts in batches:
        batch_guidelines = guidelines[processed : processed + len(batch_texts)]
        processed += len(batch_texts)

        if all(g.id in done_ids for g in batch_guidelines):
            continue

        for attempt in range(5):
            try:
                embeddings = encode_batch(batch_texts)
                break
            except RateLimitError:
                if attempt == 4:
                    raise
                wait = 60
                logger.warning("Rate limit 초과, %d초 대기 후 재시도 (%d/5)...", wait, attempt + 1)
                time.sleep(wait)

        await VectorDocument.bulk_create(
            [
                VectorDocument(
                    reference_type=REFERENCE_TYPE,
                    reference_id=g.id,
                    content=text,
                    embedding=emb,
                )
                for g, text, emb in zip(batch_guidelines, batch_texts, embeddings, strict=False)
                if g.id not in done_ids
            ]
        )
        logger.info("임베딩 진행: %d / %d", processed, total)

    await Tortoise.close_connections()
    logger.info("seed 완료")


if __name__ == "__main__":
    asyncio.run(seed())
