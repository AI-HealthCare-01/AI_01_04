"""04-seed-disease-code-mappings.json → disease_code_mappings 테이블 시드 SQL 생성.

사용법:
    python scripts/seed_disease_code_mappings.py > scripts/init-db/05-seed-disease-code-mappings.sql

또는 직접 DB에 INSERT:
    python scripts/seed_disease_code_mappings.py --execute
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
MAPPING_JSON = BASE_DIR / "scripts" / "init-db" / "04-seed-disease-code-mappings.json"


def generate_sql() -> str:
    with MAPPING_JSON.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    lines = [
        "-- Auto-generated: disease_code_mappings seed",
        "TRUNCATE disease_code_mappings RESTART IDENTITY CASCADE;",
        "",
    ]

    for row in rows:
        code = row["code"].replace("'", "''")
        name = row["name"].replace("'", "''")
        mapped_code = row["mapped_code"].replace("'", "''")
        mapped_name = row["mapped_name"].replace("'", "''")
        is_anchor = "true" if row.get("is_recommendation_anchor", False) else "false"

        lines.append(
            f"INSERT INTO disease_code_mappings (code, name, mapped_code, mapped_name, is_anchor) "
            f"VALUES ('{code}', '{name}', '{mapped_code}', '{mapped_name}', {is_anchor}) "
            f"ON CONFLICT (code) DO UPDATE SET "
            f"mapped_code = EXCLUDED.mapped_code, mapped_name = EXCLUDED.mapped_name, "
            f"is_anchor = EXCLUDED.is_anchor;"
        )

    lines.append("")
    return "\n".join(lines)


async def execute_to_db() -> None:
    import asyncpg  # type: ignore[import-untyped]  # noqa: E402

    from app.core import config  # noqa: E402

    conn = await asyncpg.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
    )

    sql = generate_sql()
    await conn.execute(sql)
    await conn.close()
    print(f"[DONE] {MAPPING_JSON} → DB disease_code_mappings 시드 완료")


def main() -> None:
    if "--execute" in sys.argv:
        asyncio.run(execute_to_db())
    else:
        print(generate_sql())


if __name__ == "__main__":
    main()
