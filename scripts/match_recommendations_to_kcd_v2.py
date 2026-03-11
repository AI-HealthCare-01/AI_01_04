from __future__ import annotations

import csv
import json
import re
from difflib import get_close_matches
from pathlib import Path

INPUT_PATH = Path("recommendation_seed.cleaned.json")
KCD_PATH = Path("../data/disease_codes.csv")
OUTPUT_PATH = Path("init-db/03-seed-recommendations.json")
UNMATCHED_PATH = Path("init-db/03-unmatched-disease-names.json")


NON_DISEASE_KEYWORDS = [
    "검사",
    "수술",
    "치료",
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
    "운동",
    "음주",
    "손씻기",
    "수혈",
    "심폐소생술",
    "장루 관리",
    "국가건강정보포털",
]

TITLE_NORMALIZATION_RULES = [
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
    (r"^얼굴마비\(말초성 마비\)$", "말초성 안면마비"),
    (r"^얼굴마비\(중추성 마비\)$", "중추성 안면마비"),
    (r"^오십견\(동결견, 유착관절낭염\)$", "오십견"),
    (r"^조갑감입\(파고드는 발톱_감입발톱\)$", "감입발톱"),
    (r"^수근굴\(수근관\) 증후군$", "수근관증후군"),
    (r"^굴절이상\(근시, 원시, 난시\)$", "굴절이상"),
]

ALIAS_MAP = {
    "간경변증": "간경화",
    "감기": "급성비인두염",
    "고혈압심장질환": "고혈압성심장질환",
    "고혈압성 콩팥병": "고혈압성신장병",
    "대사이상지방간질환": "지방간",
    "골관절염": "관절증",
    "급성 바이러스 위장관염": "바이러스장염",
    "급성 세균성 장염": "세균성장염",
    "급성부고환염": "부고환염",
    "급성신손상(소아)": "급성신손상",
    "기저귀피부염": "기저귀[냅킨]피부염",
    "낙상": "낙상",
    "남성형 탈모": "탈모증",
    "노인 보행장애": "보행장애",
    "노인 삼킴장애": "삼킴장애",
    "당뇨망막병증": "당뇨병성망막병증",
    "당뇨병성 족부병증": "당뇨병성족부병증",
    "대장게실증": "(소)(대)장의 게실증",
    "대장용종": "결장의 폴립",
    "독성 간 손상": "독성간질환",
    "만성콩팥병": "만성신장병",
    "말라리아": "말라리아",
    "발기부전": "기질적 원인에 의한 발기부전",
    "백내장": "백내장",
    "부정맥": "부정맥",
    "비부비동염": "부비동염(만성)",
    "빈혈": "빈혈",
    "사마귀": "사마귀",
    "설사": "감염성 (신생아의) 설사 NOS",
    "성매개감염병": "상세불명의 성매개질환",
    "소아발진": "발진",
    "습진": "습진",
    "식중독": "식중독",
    "신생아 황달": "상세불명의 신생아황달",
    "어지럼": "어지럼증",
    "열상": "열상",
    "염좌": "염좌",
    "요로감염": "부위가 명시되지 않은 요로감염",
    "요실금": "요실금",
    "우울감": "우울증 NOS",
    "위식도역류질환": "위-식도역류병",
    "위염": "상세불명의 위염",
    "유선염": "유방염",
    "유행각결막염": "유행성 각막결막염",
    "입덧": "임신중 과다구토",
    "자궁근종": "자궁평활근종",
    "장결핵": "장(대, 소)의 결핵",
    "전립선비대증": "전립선의 비대",
    "족저근막염": "족저근막염",
    "중이염": "상세불명의 중이염",
    "뇌수막염": "수막염",
    "뇌졸중": "뇌경색",
    "복통": "복통",
    "복부 팽만": "복부의 가스팽만",
    "구역질과 구토": "구역 및 구토",
    "알레르기": "알레르기",
    "구내염": "구내염 NOS",
    "생리통": "월경통",
    "비정상 자궁출혈": "기타 이상 자궁 및 질 출혈",
    "조산": "조기진통",
    "조기난소부전": "원발성 난소부전",
    "부신부전증": "부신기능저하증",
    "갈색세포종": "갈색세포종",
    "객혈": "객혈",
    "갑상선기능저하증": "갑상선기능저하증",
    "갑상선기능항진증": "갑상선기능항진증",
    "갑상선염": "갑상선염",
    "간흡충증": "간흡충증",
    "감염심내막염": "감염성 심내막염",
    "A형간염": "급성 A형간염",
    "B형간염": "급성 B형간염",
    "C형간염": "급성 C형간염",
    "골다공증": "상세불명의 골다공증",
    "급성 간부전": "급성 및 아급성 간부전",
    "비브리오 패혈증": "비브리오균에 의한 패혈증",
    "중증열성혈소판감소증후군(SFTS)": "중증열성혈소판감소증후군 [SFTS]",
    "노인 어지럼증": "어지럼증 및 어지럼",
    "부종": "상세불명의 부종",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_kcd_csv(path: Path):
    rows = []
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
    return text


def is_non_disease_title(name: str) -> bool:
    return any(kw in name for kw in NON_DISEASE_KEYWORDS)


def apply_title_rules(name: str) -> str | None:
    for pattern, replacement in TITLE_NORMALIZATION_RULES:
        if re.match(pattern, name):
            return replacement
    return None


def simplify_parenthesized_name(name: str) -> str | None:
    match = re.match(r"^(.*?)\((.*?)\)$", name)
    if not match:
        return None

    outer = match.group(1).strip()
    inner = match.group(2).strip()

    if inner in ALIAS_MAP:
        return ALIAS_MAP[inner]

    inner_first = re.split(r"[,_/]", inner)[0].strip()
    if inner_first:
        return inner_first

    if outer:
        return outer

    return None


def simplify_phrase_pattern(name: str) -> str | None:
    match = re.match(r"^(.*?) 환자의 .*요법$", name)
    if match:
        return match.group(1).strip()
    return None


def should_drop_title(name: str) -> bool:
    if re.search(r"(방법|관리|예방|수칙|요령|알려드리겠습니다)", name):
        return True
    if re.search(r"(검사|수술|시술|이식|마취)$", name):
        return True
    return False


def simplify_disease_name(name: str) -> str | None:
    name = name.strip()
    if not name:
        return None

    title_rule = apply_title_rules(name)
    if title_rule:
        return title_rule

    if name in ALIAS_MAP:
        return ALIAS_MAP[name]

    if is_non_disease_title(name):
        title_rule = apply_title_rules(name)
        if title_rule:
            return title_rule

    parenthesized = simplify_parenthesized_name(name)
    if parenthesized:
        return parenthesized

    phrase_based = simplify_phrase_pattern(name)
    if phrase_based:
        return phrase_based

    if should_drop_title(name):
        return None

    if name in ALIAS_MAP:
        return ALIAS_MAP[name]

    return name


def build_disease_index(diseases: list[dict]):
    exact_map: dict[str, str] = {}
    normalized_map: dict[str, str] = {}
    normalized_names: list[str] = []

    for d in diseases:
        code = str(d.get("상병기호", "")).strip()
        name = str(d.get("한글명", "")).strip()

        if not code or not name:
            continue

        exact_map[name] = code

        norm_name = normalize_name(name)
        normalized_map[norm_name] = code
        normalized_names.append(norm_name)

    return exact_map, normalized_map, normalized_names


def try_exact_or_normalized_match(
    name: str,
    exact_map: dict[str, str],
    normalized_map: dict[str, str],
) -> str | None:
    if name in exact_map:
        return exact_map[name]

    norm_name = normalize_name(name)
    if norm_name in normalized_map:
        return normalized_map[norm_name]

    return None


def try_simplified_match(
    name: str,
    exact_map: dict[str, str],
    normalized_map: dict[str, str],
) -> tuple[str | None, str]:
    simplified = simplify_disease_name(name)
    if not simplified:
        return None, name

    code = try_exact_or_normalized_match(simplified, exact_map, normalized_map)
    return code, simplified


def try_parenthesis_front_match(
    name: str,
    exact_map: dict[str, str],
    normalized_map: dict[str, str],
) -> str | None:
    simple_name = name.split("(")[0].strip()
    return try_exact_or_normalized_match(simple_name, exact_map, normalized_map)


def try_fuzzy_match(
    name: str,
    normalized_map: dict[str, str],
    normalized_names: list[str],
) -> str | None:
    norm_name = normalize_name(name)
    simple_name = name.split("(")[0].strip()
    norm_simple_name = normalize_name(simple_name)

    match = get_close_matches(norm_name, normalized_names, n=1, cutoff=0.82)
    if match:
        return normalized_map[match[0]]

    match2 = get_close_matches(norm_simple_name, normalized_names, n=1, cutoff=0.82)
    if match2:
        return normalized_map[match2[0]]

    return None


def match_disease(
    name: str,
    exact_map: dict[str, str],
    normalized_map: dict[str, str],
    normalized_names: list[str],
) -> str | None:
    if not name:
        return None

    code = try_exact_or_normalized_match(name, exact_map, normalized_map)
    if code:
        return code

    simplified_code, simplified_name = try_simplified_match(name, exact_map, normalized_map)
    if simplified_code:
        return simplified_code

    code = try_parenthesis_front_match(simplified_name, exact_map, normalized_map)
    if code:
        return code

    return try_fuzzy_match(simplified_name, normalized_map, normalized_names)


def main():
    seeds = load_json(INPUT_PATH)
    diseases = load_kcd_csv(KCD_PATH)

    exact_map, normalized_map, normalized_names = build_disease_index(diseases)

    results = []
    misses = {}

    for row in seeds:
        disease_name = str(row.get("disease_name", "")).strip()
        category = str(row.get("category", "")).strip()
        content = str(row.get("content", "")).strip()

        if not disease_name or not category or not content:
            continue

        simplified_name = simplify_disease_name(disease_name)

        if not simplified_name:
            misses[disease_name] = {
                "reason": "non_disease_title",
                "normalized_name": None,
            }
            continue

        code = match_disease(
            simplified_name,
            exact_map,
            normalized_map,
            normalized_names,
        )

        if not code:
            misses[disease_name] = {
                "reason": "no_match",
                "normalized_name": simplified_name,
            }
            continue

        results.append(
            {
                "disease_code": code,
                "disease_name": simplified_name,
                "original_disease_name": disease_name,
                "category": category,
                "content": content,
                "source": row.get("source", "kdca_healthinfo"),
            }
        )

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    with UNMATCHED_PATH.open("w", encoding="utf-8") as f:
        json.dump(misses, f, ensure_ascii=False, indent=2)

    print("=== recommendation seed + 상병코드 매칭 완료 ===")
    print(f"입력 seed 수: {len(seeds)}")
    print(f"매칭 성공 수: {len(results)}")
    print(f"매칭 실패 질환명 수: {len(misses)}")
    print(f"저장 파일: {OUTPUT_PATH}")
    print(f"실패 목록 파일: {UNMATCHED_PATH}")


if __name__ == "__main__":
    main()
