from __future__ import annotations

import json
from pathlib import Path
from typing import Any


INPUT_PATH = Path("init-db/03-unmatched-disease-names.json")
OUTPUT_PATH = Path("init-db/03-unmatched-classified.json")


NON_DISEASE_TITLE_KEYWORDS = [
    "검사",
    "수술",
    "시술",
    "이식",
    "마취",
    "재활",
    "식이요법",
    "운동요법",
    "약물요법",
    "관리방법",
    "예방요령",
    "예방수칙",
    "건강수칙",
    "건강문제",
    "관리",
    "방법",
    "요령",
    "알려드리겠습니다",
    "국가건강정보포털",
    "질병관리청",
]


TOPIC_KEYWORDS = [
    "건강노화",
    "건강기능식품",
    "간접흡연",
    "공기 오염",
    "운동",
    "음주",
    "손씻기",
    "식이영양",
    "신체활동",
    "건강하게",
    "체중조절",
    "다중화학물질과민증",
    "고위험 임산부",
    "겨울철",
    "한파",
    "폭염",
    "대설",
    "생활 속의",
    "성공적인 모유 수유",
]


SYMPTOM_KEYWORDS = [
    "부종",
    "복통",
    "설사",
    "어지럼",
    "어지럼증",
    "구역",
    "구토",
    "발열",
    "객혈",
    "혈뇨",
    "단백뇨",
    "농뇨",
    "호흡곤란",
    "통증",
    "종괴",
    "황달",
    "혈변",
    "흑혈변",
    "안면홍조",
    "입덧",
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def classify_unmatched_title(name: str, meta: dict[str, Any]) -> str:
    reason = meta.get("reason")

    if reason == "non_disease_title":
        return "drop_non_disease"

    for kw in NON_DISEASE_TITLE_KEYWORDS:
        if kw in name:
            return "drop_non_disease"

    for kw in TOPIC_KEYWORDS:
        if kw in name:
            return "topic_only"

    for kw in SYMPTOM_KEYWORDS:
        if kw in name:
            return "need_manual_review_symptom"

    return "need_manual_review"


def main() -> None:
    data = load_json(INPUT_PATH)

    classified: dict[str, list[dict[str, Any]]] = {
        "drop_non_disease": [],
        "topic_only": [],
        "need_manual_review_symptom": [],
        "need_manual_review": [],
    }

    for disease_name, meta in data.items():
        group = classify_unmatched_title(disease_name, meta)
        classified[group].append(
            {
                "disease_name": disease_name,
                "reason": meta.get("reason"),
                "normalized_name": meta.get("normalized_name"),
            }
        )

    # 정렬
    for key in classified:
        classified[key] = sorted(
            classified[key],
            key=lambda x: x["disease_name"],
        )

    save_json(OUTPUT_PATH, classified)

    print("=== unmatched 질환명 자동 분류 완료 ===")
    print(f"입력 실패 질환명 수: {len(data)}")
    for key, items in classified.items():
        print(f"{key}: {len(items)}")
    print(f"저장 파일: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()