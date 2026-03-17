"""
약품 마스터 데이터 seed 스크립트.

raw_drug_license_info.xlsx → drugs 테이블 적재 후
챗봇용 vector_documents 임베딩 생성 (OpenAI text-embedding-3-small, 1536차원).

실행:
    uv run python scripts/seed_drugs.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from pathlib import Path

import pandas as pd
import tiktoken
from openai import RateLimitError
from tortoise import Tortoise

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.databases import TORTOISE_ORM
from app.models.drugs import Drug
from app.models.vector_documents import VectorDocument
from app.services.embedding import encode_batch

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

XLSX_PATH = Path(__file__).parent / "raw_drug_license_info.xlsx"
MAX_TOKENS_PER_REQUEST = 250_000  # OpenAI 한도 300,000에서 여유분 확보
REFERENCE_TYPE = "drug"

_tokenizer = tiktoken.get_encoding("cl100k_base")  # text-embedding-3-small 인코딩
MAX_TOKENS_PER_TEXT = 8000  # 8192 한도에서 decode 경계 오차 여유분 확보


def _truncate_to_tokens(text: str) -> str:
    """단일 텍스트가 8192 토큰을 초과하면 잘라낸다."""
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


def _str_or_none(val) -> str | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None


def _build_embed_text(row: pd.Series) -> str:
    """챗봇 검색용 임베딩 텍스트 구성."""
    fields = [
        ("약품명", str(row["품목명"]).strip()),
        ("주성분", _str_or_none(row["주성분명"])),
        ("원료성분", _str_or_none(row["원료성분"])),
        ("효능효과", _str_or_none(row["효능효과"])),
        ("용법용량", _str_or_none(row["용법용량"])),
        ("사용상의주의사항", _str_or_none(row["사용상의주의사항1"])),
    ]
    return "\n".join(f"{k}: {v}" for k, v in fields if v)


async def seed() -> None:
    await Tortoise.init(config=TORTOISE_ORM)

    logger.info("xlsx 로딩 중...")
    df = pd.read_excel(XLSX_PATH)
    total = len(df)
    logger.info("총 %d건 처리 시작", total)

    existing_drug_count = await Drug.all().count()
    if existing_drug_count == total:
        logger.info("drugs 이미 %d건 존재, 적재 스킵", existing_drug_count)
        drug_objs = await Drug.all().order_by("id")
    else:
        await VectorDocument.filter(reference_type=REFERENCE_TYPE).delete()
        await Drug.all().delete()
        logger.info("drugs 테이블 적재 중...")
        await Drug.bulk_create(
            [
                Drug(
                    name=str(row["품목명"]).strip(),
                    manufacturer=_str_or_none(row["업체명"]),
                    raw_material=_str_or_none(row["원료성분"]),
                    raw_material_en=_str_or_none(row["영문성분명"]),
                    efficacy=_str_or_none(row["효능효과"]),
                    dosage=_str_or_none(row["용법용량"]),
                    caution_1=_str_or_none(row["사용상의주의사항1"]),
                    caution_2=_str_or_none(row["사용상의주의사항2"]),
                    caution_3=_str_or_none(row["사용상의주의사항3"]),
                    caution_4=_str_or_none(row["사용상의주의사항4"]),
                    storage=_str_or_none(row["저장방법"]),
                    change_log=_str_or_none(row["변경내용"]),
                    main_ingredient=_str_or_none(row["주성분명"]),
                )
                for _, row in df.iterrows()
            ]
        )
        drug_objs = await Drug.all().order_by("id")
        logger.info("drugs %d건 적재 완료", len(drug_objs))

    # 2) 임베딩 텍스트 생성 후 토큰 수 기준 동적 배치 분할
    all_texts = [_truncate_to_tokens(_build_embed_text(row)) for _, row in df.iterrows()]
    batches = _make_batches(all_texts)
    logger.info("임베딩 배치 수: %d", len(batches))

    # 이미 임베딩된 drug_id 조회 — 재실행 시 중복 처리 방지
    done_ids = set(await VectorDocument.filter(reference_type=REFERENCE_TYPE).values_list("reference_id", flat=True))
    logger.info("이미 완료된 임베딩: %d건 스킵", len(done_ids))

    # 3) 배치별 임베딩 + vector_documents 적재
    processed = 0
    for batch_texts in batches:
        batch_drugs = drug_objs[processed : processed + len(batch_texts)]
        processed += len(batch_texts)

        # 이미 완료된 배치는 스킵
        if all(d.id in done_ids for d in batch_drugs):
            continue

        # 429 에러 시 최대 5회 재시도
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
                    reference_id=drug.id,
                    content=text,
                    embedding=emb,
                )
                for drug, text, emb in zip(batch_drugs, batch_texts, embeddings, strict=False)
                if drug.id not in done_ids
            ]
        )
        logger.info("임베딩 진행: %d / %d", processed, total)

    await Tortoise.close_connections()
    logger.info("seed 완료")


if __name__ == "__main__":
    asyncio.run(seed())
