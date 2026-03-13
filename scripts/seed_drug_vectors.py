from __future__ import annotations

import asyncio
import logging

from tortoise import Tortoise

from app.core.config import Config
from app.models.drugs import Drug
from app.repositories.vector_document_repository import VectorDocumentRepository
from app.services.embedding import encode

logger = logging.getLogger(__name__)

BATCH_SIZE = 2048
MAX_RETRIES = 3
RETRY_DELAY = 5


async def init_db() -> None:
    """
    시드 작업을 위한 DB 연결을 초기화한다.
    """
    cfg = Config()
    await Tortoise.init(
        db_url=f"asyncpg://{cfg.DB_USER}:{cfg.DB_PASSWORD}@{cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}",
        modules={"models": ["app.models.drugs", "app.models.vector_documents"]},
    )


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    텍스트 배열을 OpenAI 임베딩 벡터 배열로 변환한다.

    Args:
        texts (list[str]):
            임베딩할 텍스트 목록 (최대 2048개)

    Returns:
        list[list[float]]:
            각 텍스트에 대한 1536차원 임베딩 벡터 목록
    """
    from openai import OpenAI
    client = OpenAI(api_key=Config().OPENAI_API_KEY)
    response = client.embeddings.create(input=texts, model="text-embedding-3-small")
    return [item.embedding for item in response.data]


async def seed_drug_vectors() -> None:
    """
    drugs 테이블의 약물명을 임베딩하여 vector_documents 테이블에 저장한다.

    처리 규칙:
    - reference_type은 'drug'으로 고정한다.
    - reference_id는 Drug.id를 사용한다.
    - 이미 저장된 약물은 skip한다.
    - 임베딩 실패 시 MAX_RETRIES만큼 재시도한다.
    """
    repo = VectorDocumentRepository()
    drugs = await Drug.all()
    total = len(drugs)
    logger.info("총 %d개 약물 임베딩 시작", total)

    for i in range(0, total, BATCH_SIZE):
        batch_drugs = drugs[i:i + BATCH_SIZE]
        batch_names = [drug.name for drug in batch_drugs]
        # 이미 저장된 약물은 skip
        existing = await repo.list_by_reference_type_and_ids(
            reference_type="drug",
            reference_ids=[drug.id for drug in batch_drugs],
        )
        existing_ids = {doc.reference_id for doc in existing}
        new_drugs = [drug for drug in batch_drugs if drug.id not in existing_ids]
        if not new_drugs:
            logger.info("배치 %d/%d 약물 이미 저장됨, skip", i, i + len(batch_drugs))
            continue
        for attempt in range(MAX_RETRIES):
            try:
                new_names = [drug.name for drug in new_drugs]
                embeddings = await embed_batch(new_names)
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning("배치 임베딩 실패 (시도 %d/%d): %s", attempt + 1, MAX_RETRIES, e)
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error("배치 임베딩 최종 실패, skip: %s", e)
                    embeddings = None
        if embeddings is None:
            continue

        for drug, embedding in zip(new_drugs, embeddings):
            await repo.create(
                reference_type="drug",
                reference_id=drug.id,
                content=drug.name,
                embedding=embedding,
            )
        logger.info("배치 %d~%d 저장 완료", i, i + len(batch_drugs))


async def main() -> None:
    """
    약물 벡터 시드 스크립트 실행 진입점.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    await init_db()
    try:
        await seed_drug_vectors()
    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
