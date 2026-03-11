from __future__ import annotations

import asyncio

from tortoise import Tortoise

from app.core.config import Config
from app.repositories.vector_document_repository import VectorDocumentRepository
from app.services.embedding import encode

GUIDELINES = [
    {"disease": "고혈압", "content": "고혈압 환자는 저염식이를 실천하고 규칙적인 유산소 운동을 권장합니다."},
    {"disease": "당뇨", "content": "당뇨 환자는 혈당 지수가 낮은 식품을 선택하고 식후 혈당을 꾸준히 측정하세요."},
    {"disease": "고지혈증", "content": "고지혈증은 포화지방 섭취를 줄이고 오메가3가 풍부한 식품을 섭취하세요"},
]


async def main() -> None:
    cfg = Config()
    await Tortoise.init(
        db_url=f"asyncpg://{cfg.DB_USER}:{cfg.DB_PASSWORD}@{cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}",
        modules={"models": ["app.models.vector_documents"]},
    )

    repo = VectorDocumentRepository()

    for i, item in enumerate(GUIDELINES, start=1):
        vector = encode(item["content"])
        await repo.create(
            reference_type="disease_guideline",
            reference_id=i,
            content=item["content"],
            embedding=vector,
        )
        print(f"저장 완료: {item['disease']}")

    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
