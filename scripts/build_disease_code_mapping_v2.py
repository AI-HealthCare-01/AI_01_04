"""상세 KCD 코드 → 추천 anchor 코드 매핑 빌드 스크립트 (prefix 기반 확장).

기존 build_disease_code_mapping.py의 강제 정책(당뇨/고혈압 2개)만으로는
전체 47,000+ 상병기호 중 4.4%만 매핑되었음.

이 스크립트는 prefix 기반 매핑을 추가하여 커버리지를 대폭 높인다.

매핑 우선순위:
1. 강제 질환군 정책 (FORCED_GROUP_POLICY)
2. exact match (코드 자체가 anchor)
3. prefix match (코드를 한 글자씩 줄여가며 anchor 탐색)
4. 이름 기반 보조 매핑 (NAME_POLICY)

사용법:
    python -m scripts.build_disease_code_mapping_v2
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DISEASE_CODES_CSV_PATH = BASE_DIR / "scripts" / "init-db" / "03-disease_codes.csv"
RECOMMENDATION_JSON_PATH = BASE_DIR / "scripts" / "init-db" / "03-seed-recommendations.json"

OUTPUT_CSV_PATH = BASE_DIR / "scripts" / "init-db" / "04-disease_codes_with_mapping.csv"
OUTPUT_JSON_PATH = BASE_DIR / "scripts" / "init-db" / "04-seed-disease-code-mappings.json"

# 강제 질환군 매핑: 특정 prefix → 특정 anchor
FORCED_GROUP_POLICY: dict[str, str] = {
    "I10": "I10",
    "E10": "E14",
    "E11": "E14",
    "E12": "E14",
    "E13": "E14",
    "E14": "E14",
}

# 이름 키워드 → anchor 코드 보조 매핑
NAME_POLICY: dict[str, str] = {
    "고혈압": "I10",
    "당뇨": "E14",
}


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(str(text).strip().split())


def load_recommendation_anchors(path: Path) -> dict[str, str]:
    """recommendation seed에서 disease_code → disease_name anchor 추출."""
    with path.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    code_to_name: dict[str, str] = {}
    for row in rows:
        code = normalize_text(row.get("disease_code", "")).upper()
        name = normalize_text(row.get("disease_name", ""))
        if code and name and code not in code_to_name:
            code_to_name[code] = name
    return code_to_name


def load_disease_codes_csv(path: Path) -> list[dict[str, str]]:
    """03-disease_codes.csv에서 고유 상병기호/한글명 읽기."""
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        by_code: dict[str, dict[str, str]] = {}
        for row in reader:
            normalized = {(k.strip() if k else ""): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            code = normalize_text(normalized.get("상병기호", "")).upper()
            name = normalize_text(normalized.get("한글명", ""))
            if code and name and code not in by_code:
                by_code[code] = {"code": code, "name": name}
    return list(by_code.values())


def find_anchor_by_prefix(code: str, anchors: dict[str, str]) -> tuple[str, str] | None:
    """코드를 한 글자씩 줄여가며 anchor를 찾는다.

    예: E1180 → E118 → E11 → E1 순으로 탐색.
    최소 3글자(알파벳1 + 숫자2)까지만 시도.
    """
    upper = code.upper()
    # 자기 자신부터 시작해서 줄여감
    for length in range(len(upper), 2, -1):
        prefix = upper[:length]
        if prefix in anchors:
            return prefix, anchors[prefix]
    return None


def map_code(code: str, name: str, anchors: dict[str, str]) -> tuple[str, str] | None:
    """매핑 우선순위: 강제정책 → exact → prefix → 이름기반."""
    upper = code.upper()
    prefix3 = upper[:3]

    # 1. 강제 질환군 매핑
    forced = FORCED_GROUP_POLICY.get(prefix3)
    if forced and forced in anchors:
        return forced, anchors[forced]

    # 2. exact match
    if upper in anchors:
        return upper, anchors[upper]

    # 3. prefix match (핵심 확장)
    result = find_anchor_by_prefix(upper, anchors)
    if result:
        return result

    # 4. 이름 기반 보조 매핑
    normalized_name = normalize_text(name)
    for keyword, target_code in NAME_POLICY.items():
        if keyword in normalized_name and target_code in anchors:
            return target_code, anchors[target_code]

    return None


def build_mappings(
    disease_rows: list[dict[str, str]],
    anchors: dict[str, str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    mapped: list[dict[str, str]] = []
    unmatched: list[dict[str, str]] = []

    for row in disease_rows:
        code, name = row["code"], row["name"]
        result = map_code(code, name, anchors)

        if result is None:
            unmatched.append({"code": code, "name": name})
            continue

        mapped_code, mapped_name = result
        mapped.append(
            {
                "code": code,
                "name": name,
                "mapped_code": mapped_code,
                "mapped_name": mapped_name,
                "is_recommendation_anchor": str(code == mapped_code).lower(),
            }
        )

    return mapped, unmatched


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = ["code", "name", "mapped_code", "mapped_name", "is_recommendation_anchor"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, str]]) -> None:
    json_rows = [
        {
            "code": r["code"],
            "name": r["name"],
            "mapped_code": r["mapped_code"],
            "mapped_name": r["mapped_name"],
            "is_recommendation_anchor": r["is_recommendation_anchor"] == "true",
        }
        for r in rows
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(json_rows, f, ensure_ascii=False, indent=2)


def main() -> None:
    anchors = load_recommendation_anchors(RECOMMENDATION_JSON_PATH)
    disease_rows = load_disease_codes_csv(DISEASE_CODES_CSV_PATH)

    mapped, unmatched = build_mappings(disease_rows, anchors)

    write_csv(OUTPUT_CSV_PATH, mapped)
    write_json(OUTPUT_JSON_PATH, mapped)

    total = len(disease_rows)
    print(f"[DONE] total disease codes (unique): {total}")
    print(f"[DONE] mapped: {len(mapped)} ({len(mapped) / total * 100:.1f}%)")
    print(f"[DONE] unmatched: {len(unmatched)} ({len(unmatched) / total * 100:.1f}%)")
    print(f"[DONE] csv: {OUTPUT_CSV_PATH}")
    print(f"[DONE] json: {OUTPUT_JSON_PATH}")

    # 샘플 출력
    samples = {"E14", "E118", "E1180", "E1000", "I10", "I109", "J441", "M545", "K291"}
    found = [r for r in mapped if r["code"] in samples]
    if found:
        print("\n[SAMPLE]")
        for r in sorted(found, key=lambda x: x["code"]):
            print(f"  {r['code']} ({r['name']}) → {r['mapped_code']} ({r['mapped_name']})")

    if unmatched:
        print("\n[WARN] unmatched (first 20):")
        for r in unmatched[:20]:
            print(f"  {r['code']}: {r['name']}")
        if len(unmatched) > 20:
            print(f"  ... and {len(unmatched) - 20} more")


if __name__ == "__main__":
    main()
