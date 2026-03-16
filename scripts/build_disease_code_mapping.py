from __future__ import annotations

import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

DISEASE_CODES_CSV_PATH = BASE_DIR / "scripts" / "init-db" / "03-disease_codes.csv"
RECOMMENDATION_JSON_PATH = BASE_DIR / "scripts" / "init-db" / "03-seed-recommendations.json"

OUTPUT_CSV_PATH = BASE_DIR / "scripts" / "init-db" / "04-disease_codes_with_mapping.csv"
OUTPUT_JSON_PATH = BASE_DIR / "scripts" / "init-db" / "04-seed-disease-code-mappings.json"


FORCED_GROUP_POLICY = {
    "I10": "I10",
    "E10": "E14",
    "E11": "E14",
    "E12": "E14",
    "E13": "E14",
    "E14": "E14",
}

NAME_POLICY = {
    "고혈압": "I10",
    "당뇨": "E14",
}


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(str(text).strip().split())


def load_recommendation_anchors(path: Path) -> dict[str, str]:
    """
    recommendation seed에서 disease_code -> disease_name anchor 추출
    예:
    {
        "I10": "고혈압",
        "E14": "당뇨병",
        ...
    }
    """
    with path.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    if not isinstance(rows, list):
        raise ValueError("03-seed-recommendations.json must be a list")

    code_to_name: dict[str, str] = {}

    for row in rows:
        disease_code = normalize_text(row.get("disease_code", "")).upper()
        disease_name = normalize_text(row.get("disease_name", ""))

        if not disease_code or not disease_name:
            continue

        # 동일 코드가 여러 번 나와도 첫 값을 유지
        if disease_code not in code_to_name:
            code_to_name[disease_code] = disease_name

    return code_to_name


def load_disease_codes_csv(path: Path) -> list[dict[str, str]]:
    """
    03-disease_codes.csv 에서 상병기호/한글명 읽기
    같은 code가 여러 줄 있어도 1개만 남김
    """
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        print("[DEBUG] csv headers:", reader.fieldnames)

        by_code: dict[str, dict[str, str]] = {}

        for row in reader:
            normalized_row = {
                (k.strip() if k else ""): (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
            }

            code = normalize_text(normalized_row.get("상병기호", "")).upper()
            name = normalize_text(normalized_row.get("한글명", ""))

            if not code or not name:
                continue

            # 같은 상병기호는 첫 번째 한글명만 대표값으로 사용
            if code not in by_code:
                by_code[code] = {
                    "code": code,
                    "name": name,
                }

    return list(by_code.values())


def map_by_policy(code: str, name: str, anchor_code_to_name: dict[str, str]) -> tuple[str, str] | None:
    """
    매핑 우선순위
    1) 강제 질환군 정책
    2) exact match
    3) 이름 기반 보조 매핑
    """
    upper_code = code.upper()
    normalized_name = normalize_text(name)
    prefix3 = upper_code[:3]

    # 1. 강제 질환군 매핑 우선
    forced_code = FORCED_GROUP_POLICY.get(prefix3)
    if forced_code and forced_code in anchor_code_to_name:
        return forced_code, anchor_code_to_name[forced_code]

    # 2. exact match
    if upper_code in anchor_code_to_name:
        return upper_code, anchor_code_to_name[upper_code]

    # 3. 이름 기반 보조 매핑
    for keyword, target_code in NAME_POLICY.items():
        if keyword in normalized_name and target_code in anchor_code_to_name:
            return target_code, anchor_code_to_name[target_code]

    return None


def build_mappings(
    disease_rows: list[dict[str, str]],
    anchor_code_to_name: dict[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    mapped_rows: list[dict[str, str]] = []
    unmatched_rows: list[dict[str, str]] = []

    for row in disease_rows:
        code = row["code"]
        name = row["name"]

        mapped = map_by_policy(code, name, anchor_code_to_name)

        if mapped is None:
            unmatched_rows.append(
                {
                    "code": code,
                    "name": name,
                }
            )
            continue

        mapped_code, mapped_name = mapped

        mapped_row = {
            "code": code,
            "name": name,
            "mapped_code": mapped_code,
            "mapped_name": mapped_name,
            "is_recommendation_anchor": str(code == mapped_code).lower(),
        }

        mapped_rows.append(mapped_row)

    return mapped_rows, unmatched_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "code",
        "name",
        "mapped_code",
        "mapped_name",
        "is_recommendation_anchor",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, str]]) -> None:
    json_rows = [
        {
            "code": row["code"],
            "name": row["name"],
            "mapped_code": row["mapped_code"],
            "mapped_name": row["mapped_name"],
            "is_recommendation_anchor": row["is_recommendation_anchor"] == "true",
        }
        for row in rows
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(json_rows, f, ensure_ascii=False, indent=2)


def print_sample(mapped_rows: list[dict[str, str]]) -> None:
    sample_codes = {"E14", "E118", "E1000", "I10", "I109"}
    sample = [row for row in mapped_rows if row["code"] in sample_codes]

    if sample:
        print("\n[DEBUG] sample mappings:")
        for row in sample:
            print(
                f' - {row["code"]} | {row["name"]} -> '
                f'{row["mapped_code"]} | {row["mapped_name"]} '
                f'(anchor={row["is_recommendation_anchor"]})'
            )


def main() -> None:
    anchor_code_to_name = load_recommendation_anchors(RECOMMENDATION_JSON_PATH)
    disease_rows = load_disease_codes_csv(DISEASE_CODES_CSV_PATH)

    mapped_rows, unmatched_rows = build_mappings(disease_rows, anchor_code_to_name)

    write_csv(OUTPUT_CSV_PATH, mapped_rows)
    write_json(OUTPUT_JSON_PATH, mapped_rows)

    print(f"[DONE] total disease rows(unique code): {len(disease_rows)}")
    print(f"[DONE] mapped rows: {len(mapped_rows)}")
    print(f"[DONE] unmatched rows: {len(unmatched_rows)}")
    print(f"[DONE] csv output: {OUTPUT_CSV_PATH}")
    print(f"[DONE] json output: {OUTPUT_JSON_PATH}")

    print_sample(mapped_rows)

    if unmatched_rows:
        print("\n[WARN] unmatched rows (first 30):")
        for row in unmatched_rows[:30]:
            print(f' - {row["code"]}: {row["name"]}')
        if len(unmatched_rows) > 30:
            print(f" ... and {len(unmatched_rows) - 30} more")


if __name__ == "__main__":
    main()