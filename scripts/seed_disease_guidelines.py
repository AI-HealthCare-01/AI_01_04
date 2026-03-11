from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from tortoise import Tortoise

from app.core.config import Config
from app.models.diseases import Disease, DiseaseGuideline

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_JSON_PATH = BASE_DIR / "scripts" / "init-db" / "03-seed-recommendations.json"

config = Config()


# 로컬용. 실제 운영 환경에서는 환경변수로 DB 연결 정보가 주어질 것으로 예상되므로, config에서 값을 읽도록 구현
def build_db_url() -> str:
    return f"postgres://{config.DB_USER}:{config.DB_PASSWORD}@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"


async def init_db() -> None:
    await Tortoise.init(
        config={
            "connections": {"default": build_db_url()},
            "apps": {
                "models": {
                    "models": [
                        "app.models.users",
                        "app.models.diseases",
                        "app.models.recommendations",
                        "app.models.user_features",
                        "app.models.vector_documents",
                        "aerich.models",
                    ],
                    "default_connection": "default",
                }
            },
        }
    )


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("seed JSON 최상위 구조는 list 여야 합니다.")

    return data


async def get_or_create_disease(
    *,
    disease_name: str,
    disease_code: str | None,
    original_disease_name: str | None,
) -> Disease:
    disease = None

    if disease_code:
        disease = await Disease.get_or_none(icd_code=disease_code)

    if disease is None:
        disease = await Disease.get_or_none(name=disease_name)

    if disease:
        updated = False

        if not disease.icd_code and disease_code:
            disease.icd_code = disease_code
            updated = True

        if not disease.description and original_disease_name:
            disease.description = f"original_name={original_disease_name}"
            updated = True

        if updated:
            await disease.save()

        return disease

    description = f"original_name={original_disease_name}" if original_disease_name else None

    return await Disease.create(
        name=disease_name,
        icd_code=disease_code,
        description=description,
    )


async def create_guideline_if_not_exists(
    *,
    disease_id: int,
    category: str,
    content: str,
) -> bool:
    exists = await DiseaseGuideline.get_or_none(
        disease_id=disease_id,
        category=category,
        content=content,
    )
    if exists:
        return False

    await DiseaseGuideline.create(
        disease_id=disease_id,
        category=category,
        content=content,
    )
    return True


async def seed_disease_guidelines(json_path: Path) -> None:
    rows = load_json(json_path)

    disease_count = 0
    guideline_created = 0
    guideline_skipped = 0
    invalid_rows = 0

    for row in rows:
        disease_code = str(row.get("disease_code", "")).strip() or None
        disease_name = str(row.get("disease_name", "")).strip()
        original_disease_name = str(row.get("original_disease_name", "")).strip() or None
        category = str(row.get("category", "")).strip()
        content = str(row.get("content", "")).strip()

        if not disease_name or not category or not content:
            invalid_rows += 1
            print(f"[SKIP] 필수값 누락: {row}")
            continue

        disease = await get_or_create_disease(
            disease_name=disease_name,
            disease_code=disease_code,
            original_disease_name=original_disease_name,
        )
        disease_count += 1

        created = await create_guideline_if_not_exists(
            disease_id=disease.id,
            category=category,
            content=content,
        )
        if created:
            guideline_created += 1
        else:
            guideline_skipped += 1

    print("=== Seed 완료 ===")
    print(f"Disease 처리 건수: {disease_count}")
    print(f"Guideline 생성 수: {guideline_created}")
    print(f"Guideline 중복 skip 수: {guideline_skipped}")
    print(f"잘못된 row 수: {invalid_rows}")


async def main() -> None:
    await init_db()
    try:
        await seed_disease_guidelines(DEFAULT_JSON_PATH)
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
