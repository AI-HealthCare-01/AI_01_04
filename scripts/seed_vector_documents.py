from __future__ import annotations

import asyncio

from tortoise import Tortoise

from app.core.config import Config
from app.models.diseases import DiseaseGuideline
from app.repositories.vector_document_repository import VectorDocumentRepository
from app.services.embedding import encode


async def init_db() -> None:
    """
    벡터 문서 seed 작업을 위한 DB 연결을 초기화한다.
    """
    cfg = Config()
    await Tortoise.init(
        db_url=f"asyncpg://{cfg.DB_USER}:{cfg.DB_PASSWORD}@{cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}",
        modules={
            "models": [
                "app.models.diseases",
                "app.models.vector_documents",
            ]
        },
    )


async def seed_vector_documents() -> None:
    """
    DiseaseGuideline 데이터를 읽어 vector_documents 테이블에 적재한다.

    처리 규칙:
    - reference_type은 'disease_guideline'으로 고정한다.
    - reference_id는 DiseaseGuideline.id를 사용한다.
    - 이미 같은 reference_type/reference_id 문서가 있으면 중복 생성하지 않는다.
    """
    repo = VectorDocumentRepository()

    guidelines = await DiseaseGuideline.all().prefetch_related("disease")

    created_count = 0
    skipped_count = 0

    for guideline in guidelines:
        exists = await repo.get_by_reference(
            reference_type="disease_guideline",
            reference_id=guideline.id,
        )
        if exists:
            skipped_count += 1
            continue

        content = guideline.content.strip()
        if not content:
            skipped_count += 1
            continue

        vector = encode(content)

        await repo.create(
            reference_type="disease_guideline",
            reference_id=guideline.id,
            content=content,
            embedding=vector,
        )

        created_count += 1
        disease_name = guideline.disease.name if guideline.disease else "unknown"
        print(f"저장 완료: [{disease_name}] {guideline.category}")

    print("=== vector_documents seed 완료 ===")
    print(f"생성 수: {created_count}")
    print(f"skip 수: {skipped_count}")


async def main() -> None:
    """
    벡터 문서 seed 스크립트 실행 진입점.
    """
    await init_db()
    try:
        await seed_vector_documents()
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
