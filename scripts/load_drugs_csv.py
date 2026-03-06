from __future__ import annotations

import argparse
import asyncio
import csv
import os
from pathlib import Path

import asyncpg  # type: ignore[import-untyped]


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    if v is None or not v.strip():
        return default
    return v.strip()


def _build_db_config() -> dict[str, str | int]:
    # Host에서 docker postgres로 붙는 기본값(프로젝트 .env 기준)
    host = _env("DB_HOST", "127.0.0.1")
    # Host 실행 시 DB_EXPOSE_PORT 우선 사용
    port = int(_env("DB_EXPOSE_PORT", _env("DB_PORT", "15432")))
    user = _env("DB_USER", "ozcoding")
    password = _env("DB_PASSWORD", "pw1234")
    database = _env("DB_NAME", "ai_health")
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
    }


def _read_csv_rows(csv_path: Path) -> list[tuple[str, str | None]]:
    rows: list[tuple[str, str | None]] = []
    seen: set[tuple[str, str | None]] = set()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "name" not in (reader.fieldnames or []):
            raise ValueError("CSV must contain 'name' header.")

        for row in reader:
            name = (row.get("name") or "").strip()[:255]
            if not name:
                continue

            manufacturer_raw = row.get("manufacturer")
            manufacturer = manufacturer_raw.strip()[:255] if manufacturer_raw else None
            if manufacturer == "":
                manufacturer = None

            key = (name, manufacturer)
            if key in seen:
                continue
            seen.add(key)
            rows.append(key)

    return rows


async def _load(csv_path: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    db = _build_db_config()
    records = _read_csv_rows(csv_path)

    conn = await asyncpg.connect(**db)
    try:
        before_cnt = await conn.fetchval("SELECT COUNT(*) FROM drugs")

        await conn.execute("DROP TABLE IF EXISTS tmp_drugs_import")
        await conn.execute("CREATE TEMP TABLE tmp_drugs_import (name text, manufacturer text)")
        await conn.copy_records_to_table("tmp_drugs_import", records=records)

        inserted = await conn.fetchval(
            """
            WITH ins AS (
                INSERT INTO drugs(name, manufacturer)
                SELECT t.name, t.manufacturer
                FROM (
                    SELECT DISTINCT name, manufacturer
                    FROM tmp_drugs_import
                    WHERE name IS NOT NULL AND btrim(name) <> ''
                ) t
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM drugs d
                    WHERE d.name = t.name
                      AND COALESCE(d.manufacturer, '') = COALESCE(t.manufacturer, '')
                )
                RETURNING 1
            )
            SELECT COUNT(*) FROM ins
            """
        )

        after_cnt = await conn.fetchval("SELECT COUNT(*) FROM drugs")
    finally:
        await conn.close()

    print(f"csv_rows_unique={len(records)}")
    print(f"drugs_before={before_cnt}")
    print(f"inserted={inserted}")
    print(f"drugs_after={after_cnt}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load drugs CSV into drugs table.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("scripts/init-db/02-seed-drugs.csv"),
        help="CSV path (default: scripts/init-db/02-seed-drugs.csv)",
    )
    args = parser.parse_args()
    asyncio.run(_load(args.csv))


if __name__ == "__main__":
    main()
