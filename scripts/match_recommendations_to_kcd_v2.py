from __future__ import annotations

import csv
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


INPUT_PATH = Path("recommendation_seed.cleaned.json")
KCD_PATH = Path("../data/disease_codes.csv")
OUTPUT_PATH = Path("init-db/03-seed-recommendations.json")
UNMATCHED_PATH = Path("init-db/03-unmatched-disease-names.json")
DEBUG_CANDIDATES_PATH = Path("init-db/03-unmatched-candidates.json")


NON_DISEASE_KEYWORDS = [
    "검사",
    "수술",
    "시술",
    "마취",
    "이식",
    "재활",
    "운동요법",
    "식이요법",
    "약물요법",
    "관리방법",
    "예방요령",
    "예방수칙",
    "건강수칙",
    "건강문제",
    "건강노화",
    "건강기능식품",
    "심폐소생술",
    "손씻기",
    "장루 관리",
    "국가건강정보포털",
]

TITLE_NORMALIZATION_RULES: list[tuple[str, str]] = [
    (r"^고혈압 환자의 식이요법$", "고혈압"),
    (r"^고혈압 환자의 운동요법$", "고혈압"),
    (r"^당뇨환자의 식이요법$", "당뇨병"),
    (r"^당뇨환자의 운동요법$", "당뇨병"),
    (r"^당뇨환자의 약물요법$", "당뇨병"),
    (r"^노인 고혈압$", "고혈압"),
    (r"^노인 당뇨병$", "당뇨병"),
    (r"^소아 비만$", "비만"),
    (r"^고혈압과 눈.*$", "고혈압"),
    (r"^당뇨병 합병증.*$", "당뇨병"),
    (r"^노인 부종$", "부종"),
    (r"^노인 변비$", "변비"),
    (r"^노인 요실금$", "요실금"),
    (r"^노인 어지럼증$", "어지럼증"),
    (r"^소변이상\(농뇨\)$", "농뇨"),
    (r"^소변이상\(단백뇨\)$", "단백뇨"),
    (r"^소변이상\(혈뇨\)$", "혈뇨"),
    (r"^소변이상\(당뇨\)$", "당뇨병"),
    (r"^연조직염과 종기\(연조직염\)$", "연조직염"),
    (r"^안외상\(각막찰과상\)$", "각막찰과상"),
    (r"^안외상\(각막화상\)$", "각막화상"),
    (r"^안외상\(안와골절\)$", "안와골절"),
    (r"^오십견\(동결견, 유착관절낭염\)$", "오십견"),
    (r"^조갑감입\(파고드는 발톱_감입발톱\)$", "감입발톱"),
    (r"^수근굴\(수근관\) 증후군$", "수근관증후군"),
    (r"^굴절이상\(근시, 원시, 난시\)$", "굴절이상"),
    (r"^당뇨망막병증$", "당뇨병성망막병증"),
    (r"^당뇨병성 족부병증$", "당뇨병성족부병증"),
    (r"^비부비동염$", "부비동염"),
    (r"^연조직염\(봉와직염\)$", "연조직염"),
    (r"^수두증\(소아\)$", "수두증"),
    (r"^수족구병\(손발입병\)$", "수족구병"),
    (r"^중증열성혈소판감소증후군\(SFTS\)$", "중증열성혈소판감소증후군"),
]

ALIAS_MAP: dict[str, str] = {
    "간경변증": "간경변증",
    "감기": "급성비인두염",
    "고혈압심장질환": "고혈압성심장질환",
    "고혈압성 콩팥병": "고혈압성신장병",
    "대사이상지방간질환": "지방간",
    "골관절염": "관절증",
    "급성 바이러스 위장관염": "바이러스장염",
    "급성 세균성 장염": "세균성 장염",
    "급성부고환염": "부고환염",
    "급성신손상(소아)": "급성신손상",
    "기저귀피부염": "기저귀피부염",
    "남성형 탈모": "안드로젠탈모증",
    "노인 보행장애": "보행장애",
    "노인 삼킴장애": "삼킴장애",
    "당뇨망막병증": "당뇨병성망막병증",
    "당뇨병성 족부병증": "당뇨병성족부병증",
    "대장게실증": "게실증",
    "대장용종": "결장폴립",
    "독성 간 손상": "독성간질환",
    "만성콩팥병": "만성신장병",
    "부신부전증": "부신기능저하증",
    "감염심내막염": "감염성 심내막염",
    "비정상 자궁출혈": "이상자궁출혈",
    "유선염": "유방염",
    "입덧": "임신중 구토",
    "전립선비대증": "전립선의 비대",
    "뇌수막염": "수막염",
    "뇌졸중": "뇌경색",
    "어지럼": "어지럼증 및 어지럼",
    "신생아 황달": "신생아황달",
    "성매개감염병": "상세불명의 성매개질환",
    "중이염": "상세불명의 중이염",
    "발기부전": "기질적 원인에 의한 발기부전",
    "A형간염": "급성 A형간염",
    "B형간염": "급성 B형간염",
    "C형간염": "급성 C형간염",
    "급성 간부전": "급성 및 아급성 간부전",
    "비브리오 패혈증": "비브리오균에 의한 패혈증",
    "구내염": "구내염 NOS",
    "부종": "상세불명의 부종",
    "노인 부종": "상세불명의 부종",
    "노인 어지럼증": "어지럼증 및 어지럼",
    "설사": "감염성 (신생아의) 설사 NOS",
    "기저귀피부염": "기저귀[냅킨]피부염",
    "비부비동염": "부비동염(만성)",
    "대장게실증": "(소)(대)장의 게실증",
    "요로감염": "부위가 명시되지 않은 요로감염",
    "골다공증": "상세불명의 골다공증",
    "빈혈": "상세불명의 빈혈",
    "갈색세포종": "갈색세포종",
}


BAD_CANDIDATE_PATTERNS = [
    r"F44\.0-F44\.6",
    r"에 분류된 장애의 복합",
    r"NOS,? 상세불명 외에 너무 긴 설명형 후보",  # 실제 비교에는 안 씀, 문서용
]

BAD_CANDIDATE_KEYWORDS = [
    "에 분류된 장애의 복합",
]

BRACKET_DROP_WORDS = [
    "급성",
    "만성",
    "상세불명",
    "상세불명의",
    "기타",
    "NOS",
    "소아",
    "성인",
    "바이러스성",
    "감염성",
    "양성",
    "급성기",
    "만성기",
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_kcd_csv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def normalize_name(text: str) -> str:
    text = text.strip()
    text = text.replace(" ", "")
    text = text.replace("’", "").replace("'", "")
    text = text.replace("·", "")
    text = text.replace("_", "")
    text = text.replace("-", "")
    text = text.replace(",", "")
    text = text.replace(":", "")
    text = text.replace("!", "")
    text = text.replace("?", "")
    return text


def clean_kcd_name_for_compare(name: str) -> str:
    s = name.strip()

    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"\([^\)]*\)", "", s)
    s = re.sub(r"\bNOS\b", "", s, flags=re.IGNORECASE)
    s = s.replace("상세불명의", "")
    s = s.replace("상세불명", "")
    s = s.replace("기타", "")
    s = s.replace("급성", "")
    s = s.replace("만성", "")
    s = s.replace("바이러스성", "")
    s = s.replace("감염성", "")
    s = re.sub(r"\s+", " ", s).strip()

    return s


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def is_non_disease_title(name: str) -> bool:
    return any(kw in name for kw in NON_DISEASE_KEYWORDS)


def simplify_disease_name(name: str) -> str | None:
    name = name.strip()
    if not name:
        return None

    for pattern, replacement in TITLE_NORMALIZATION_RULES:
        if re.match(pattern, name):
            return replacement

    if name in ALIAS_MAP:
        return ALIAS_MAP[name]

    if re.search(r"(방법|관리|예방|수칙|요령|알려드리겠습니다)", name):
        return None

    if is_non_disease_title(name):
        return None

    m = re.match(r"^(.*?)\((.*?)\)$", name)
    if m:
        outer = m.group(1).strip()
        inner = m.group(2).strip()

        if inner in ALIAS_MAP:
            return ALIAS_MAP[inner]

        inner_first = re.split(r"[,_/]", inner)[0].strip()
        if inner_first and inner_first not in BRACKET_DROP_WORDS:
            return inner_first

        if outer:
            return outer

    m2 = re.match(r"^(.*?) 환자의 .*요법$", name)
    if m2:
        return m2.group(1).strip()

    if re.search(r"(검사|수술|시술|이식|마취)$", name):
        return None

    return name


def is_bad_candidate(name: str) -> bool:
    if any(word in name for word in BAD_CANDIDATE_KEYWORDS):
        return True
    return False


def build_disease_index(diseases: list[dict[str, str]]) -> list[dict[str, str]]:
    indexed: list[dict[str, str]] = []

    for row in diseases:
        code = str(row.get("상병기호", "")).strip()
        name = str(row.get("한글명", "")).strip()
        if not code or not name:
            continue

        compare_name = clean_kcd_name_for_compare(name)

        indexed.append(
            {
                "code": code,
                "name": name,
                "compare_name": compare_name,
                "norm_name": normalize_name(name),
                "norm_compare_name": normalize_name(compare_name),
            }
        )

    return indexed


def find_best_candidates(name: str, disease_index: list[dict[str, str]], top_n: int = 5) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    target = simplify_disease_name(name)
    if not target:
        return results

    target_norm = normalize_name(target)

    for item in disease_index:
        if is_bad_candidate(item["name"]):
            continue

        score1 = similarity(target, item["name"])
        score2 = similarity(target, item["compare_name"])
        score3 = SequenceMatcher(None, target_norm, item["norm_name"]).ratio()
        score4 = SequenceMatcher(None, target_norm, item["norm_compare_name"]).ratio()
        final_score = max(score1, score2, score3, score4)

        if target_norm and target_norm in item["norm_name"]:
            final_score = max(final_score, 0.93)
        if target_norm and target_norm in item["norm_compare_name"]:
            final_score = max(final_score, 0.95)

        results.append(
            {
                "candidate_name": item["name"],
                "candidate_code": item["code"],
                "score": round(final_score, 4),
            }
        )

    results.sort(key=lambda x: (-x["score"], x["candidate_name"]))
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for r in results:
        key = (r["candidate_code"], r["candidate_name"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
        if len(deduped) >= top_n:
            break

    return deduped


def choose_code(name: str, disease_index: list[dict[str, str]]) -> tuple[str | None, list[dict[str, Any]]]:
    target = simplify_disease_name(name)
    if not target:
        return None, []

    if target in ALIAS_MAP:
        target = ALIAS_MAP[target]

    candidates = find_best_candidates(target, disease_index, top_n=5)
    if not candidates:
        return None, []

    best = candidates[0]

    # 매우 신뢰 높은 경우 자동 매칭
    if best["score"] >= 0.97:
        return best["candidate_code"], candidates

    # 상위 후보가 충분히 납득되는 경우
    if best["score"] >= 0.93:
        return best["candidate_code"], candidates

    return None, candidates


def main() -> None:
    seeds = load_json(INPUT_PATH)
    diseases = load_kcd_csv(KCD_PATH)
    disease_index = build_disease_index(diseases)

    matched_rows: list[dict[str, Any]] = []
    unmatched: dict[str, Any] = {}
    debug_candidates: dict[str, Any] = {}

    for row in seeds:
        disease_name = str(row.get("disease_name", "")).strip()
        category = str(row.get("category", "")).strip()
        content = str(row.get("content", "")).strip()

        if not disease_name or not category or not content:
            continue

        simplified = simplify_disease_name(disease_name)
        if not simplified:
            unmatched[disease_name] = {
                "reason": "non_disease_title",
                "normalized_name": None,
            }
            continue

        code, candidates = choose_code(simplified, disease_index)

        if not code:
            unmatched[disease_name] = {
                "reason": "no_match",
                "normalized_name": simplified,
            }
            debug_candidates[disease_name] = {
                "manual_alias": ALIAS_MAP.get(disease_name),
                "candidates": candidates,
            }
            continue

        matched_rows.append(
            {
                "disease_code": code,
                "disease_name": simplified,
                "original_disease_name": disease_name,
                "category": category,
                "content": content,
                "source": row.get("source", "kdca_healthinfo"),
            }
        )

    save_json(OUTPUT_PATH, matched_rows)
    save_json(UNMATCHED_PATH, unmatched)
    save_json(DEBUG_CANDIDATES_PATH, debug_candidates)

    print("=== recommendation seed + 상병코드 매칭 완료 ===")
    print(f"입력 seed 수: {len(seeds)}")
    print(f"매칭 성공 수: {len(matched_rows)}")
    print(f"매칭 실패 질환명 수: {len(unmatched)}")
    print(f"저장 파일: {OUTPUT_PATH}")
    print(f"실패 목록 파일: {UNMATCHED_PATH}")
    print(f"후보 디버그 파일: {DEBUG_CANDIDATES_PATH}")


if __name__ == "__main__":
    main()