from __future__ import annotations

import json
import re

from openai import AsyncOpenAI

from app.core import config

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    """OCR 후처리용 AsyncOpenAI 싱글턴 인스턴스를 반환한다."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=config.OPENAI_API_KEY,
            timeout=15.0,
            max_retries=1,
        )
    return _client


PRESCRIPTION_SYSTEM_PROMPT = """\
한국 처방전 OCR 후처리기. JSON만 반환.
출력 키: document_date, diagnosis_list, drugs.
- document_date: "YYYY-MM-DD" | null
- diagnosis_list: "KCD코드 진단명" 문자열 배열. 여러 개면 모두 추출. 없으면 []
  처방전에 코드만 있고 진단명이 없으면, KCD 코드에 해당하는 한국어 진단명을 의학 지식으로 추론하여 "코드 진단명" 형식으로 반환.
  예: "U071 코로나바이러스감염증-19", "J209 급성 기관지염", "I10 본태성 고혈압"
  hints.codes에 후보가 있으면 신뢰하되, 처방약으로 추론 가능한 누락 코드는 추가.
- drugs: 배열. 각 항목 필드: name, edi_code, dose_amount, dose_unit, dose_count, dose_timing, dose_days. 없으면 []
  - name: 처방전 원문의 약품명을 함량·제형 포함하여 그대로 출력. 예: "노바스크정5mg", "트라젠타듀오정2.5/1정". "(내복)/1정" 같은 투여경로·수량 접미사는 제거하되, 함량(mg, 밀리그램 등)과 제형(정, 캡슐 등)은 반드시 포함. 축약 금지. 불가시 "인식 불가"
  - edi_code: 약품명 앞에 있는 9자리 숫자 코드(보험코드). 예: "648900030". 반드시 추출. 없으면 null
  - dose_amount: "1회투여량" 칸의 숫자 문자열 | null
  - dose_unit: 정,ml,캡슐,방울 등 | null
  - dose_count: "1일투여횟수" 칸의 숫자를 정확히 읽어서 정수로 반환. 처방전 표에서 해당 약품 행의 "1일투여횟수" 열 값을 그대로 사용. 절대 임의로 변경하지 말 것. null 금지 — 읽을 수 없으면 1.
  - dose_timing 허용값: "식후","식전","아침 식후","아침 식전","점심 식후","점심 식전","저녁 식후","저녁 식전","자기 전","필요시" | null
  - dose_days: "총투약일수" 칸의 숫자를 정수로 반환 | null
  처방전은 표 형식이며 각 약품 행에 1회투여량, 1일투여횟수, 총투약일수 열이 있다.
  각 열의 숫자를 해당 약품 행에서 정확히 읽어 매핑할 것.
  용법란("용법","복용법","투약방법")이 있으면 dose_timing에 반영.
  dose_timing이 "식후" 또는 "식전"이면 dose_count로 복용 시간대를 자동 결정하므로, 특정 시간대가 명시되지 않은 경우 "식후"를 기본값으로 사용.
  "필요시"는 용법에 "필요시","필요할 때","PRN","가려울 때","기침 시" 등 증상 발생 시 복용하라고 명시된 경우에만 사용. 그 외 모든 약품(점안액·외용제·하루 N회 투여 포함)은 "식후"를 기본값으로 설정.
"""


MEDICAL_RECORD_SYSTEM_PROMPT = """\
한국 진료기록지 OCR 후처리기. JSON만 반환.
출력 키: document_date, diagnosis_list, clinical_note, drugs.
- document_date: "YYYY-MM-DD" | null
- diagnosis_list: 진단명/KCD코드 배열. 없으면 []
- clinical_note: 진료내용·소견·지도 요약 문자열 | null
- drugs: [{name, dose_amount, dose_unit, dose_count, dose_timing, dose_days}]. 명확한 약물만. 없으면 []
확실하지 않으면 null.
"""


def _get_system_prompt(document_type: str) -> str:
    """문서 유형에 따라 시스템 프롬프트를 반환한다."""
    if document_type == "medical_record":
        return MEDICAL_RECORD_SYSTEM_PROMPT
    return PRESCRIPTION_SYSTEM_PROMPT


def _extract_json_object(text: str) -> dict:
    """모델 출력에서 JSON 객체만 최대한 복구해서 파싱한다."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        result = json.loads(candidate)
        if isinstance(result, dict):
            return result

    raise ValueError("AI postprocess result must be a valid JSON object")


async def ai_postprocess(
    raw_text: str,
    ocr_raw: dict,
    document_type: str = "prescription",
    parser_hints: dict | None = None,
) -> dict:
    """OCR 결과를 OpenAI로 후처리하여 구조화된 dict를 반환한다."""
    client = get_openai_client()
    system_prompt = _get_system_prompt(document_type)
    parser_hints = parser_hints or {}

    user_payload = {
        "t": document_type,
        "text": raw_text,
        "hints": {
            "dates": parser_hints.get("candidate_dates", []),
            "codes": parser_hints.get("candidate_diagnosis_codes", []),
            "drugs": parser_hints.get("candidate_drugs", []),
        },
    }

    response = await client.responses.create(
        model=config.OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        text={"format": {"type": "json_object"}},
        temperature=0.2,
        max_output_tokens=2048,
    )

    text = response.output_text
    result = _extract_json_object(text)

    result.setdefault("document_date", None)
    result.setdefault("diagnosis_list", [])
    result.setdefault("clinical_note", None)
    result.setdefault("drugs", [])
    result.setdefault("raw_text", raw_text)
    result["ocr_raw"] = ocr_raw  # LLM 응답과 무관하게 원본 그대로 저장

    if not isinstance(result.get("diagnosis_list"), list):
        result["diagnosis_list"] = []
    if not isinstance(result.get("drugs"), list):
        result["drugs"] = []

    result = _merge_parser_hints(result, parser_hints)

    # drugs를 DrugEntry 호환 dict 목록으로 정규화
    normalized_drugs: list[dict] = []
    unrecognized: list[str] = []
    for d in result["drugs"]:
        if isinstance(d, str):
            if d == "인식 불가":
                unrecognized.append(d)
            else:
                normalized_drugs.append({"name": d})
        elif isinstance(d, dict) and d.get("name"):
            if d["name"] == "인식 불가":
                unrecognized.append(d["name"])
            else:
                d["name"] = _fix_drug_name(d["name"])
                if d.get("dose_unit"):
                    d["dose_unit"] = _fix_dose_unit(d["dose_unit"])
                normalized_drugs.append(d)
    result["drugs"] = normalized_drugs
    result["unrecognized_drugs"] = unrecognized

    # AI가 못 잡은 KCD 코드를 raw_text에서 직접 추출하여 보완
    if not result["diagnosis_list"]:
        result["diagnosis_list"] = _extract_kcd_codes(raw_text)

    return result


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _drug_name(item: str | dict) -> str:
    """drugs 항목에서 약품명을 추출한다."""
    if isinstance(item, dict):
        return str(item.get("name", "")).strip()
    return str(item).strip()


def _dedupe_drugs(items: list) -> list[dict]:
    """drugs 리스트를 dict 형태로 정규화하고 중복을 제거한다."""
    seen: set[str] = set()
    result: list[dict] = []
    for item in items:
        name = _drug_name(item)
        if not name or name in seen:
            continue
        seen.add(name)
        result.append(item if isinstance(item, dict) else {"name": name})
    return result


# 유효한 KCD 코드 첫 글자 (ICD-10 챕터)
_VALID_KCD_PREFIXES = set("ABCDEFGHIJKLMNOPQRSTUV")


def _is_valid_kcd(code: str) -> bool:
    """KCD/ICD-10 형식인지 검증한다."""
    code = code.strip()
    if len(code) < 3:
        return False
    return code[0] in _VALID_KCD_PREFIXES and re.fullmatch(r"[A-Z]\d{2,4}[0-9A-Z]?", code) is not None


def _reconcile_diagnosis(
    diagnosis_list: list[str],
    candidate_codes: list[str],
) -> list[str]:
    """AI diagnosis_list와 parser 후보 코드를 비교하여 병합한다."""
    kept: list[str] = []
    used_codes: set[str] = set()
    for diag in diagnosis_list:
        matched = False
        for code in candidate_codes:
            if code in diag:
                kept.append(diag)
                used_codes.add(code)
                matched = True
                break
        if not matched:
            kept.append(diag)
    for code in candidate_codes:
        if code not in used_codes and _is_valid_kcd(code):
            kept.append(code)
    return _dedupe_keep_order(kept)


def _merge_parser_hints(result: dict, parser_hints: dict) -> dict:
    """AI 결과가 빈약하거나 부정확할 때 parser 후보로 보완/교체한다."""
    candidate_codes = [
        item for item in parser_hints.get("candidate_diagnosis_codes", []) if isinstance(item, str) and item.strip()
    ]
    candidate_drugs = [
        item for item in parser_hints.get("candidate_drugs", []) if isinstance(item, str) and item.strip()
    ]

    diagnosis_list = [item for item in result.get("diagnosis_list", []) if isinstance(item, str) and item.strip()]
    existing_drugs = [item for item in result.get("drugs", []) if _drug_name(item)]

    if candidate_codes and diagnosis_list:
        result["diagnosis_list"] = _reconcile_diagnosis(diagnosis_list, candidate_codes)
    elif not diagnosis_list and candidate_codes:
        result["diagnosis_list"] = _dedupe_keep_order(candidate_codes[:5])
    else:
        result["diagnosis_list"] = _dedupe_keep_order(diagnosis_list)

    if not existing_drugs and candidate_drugs:
        result["drugs"] = _dedupe_drugs(candidate_drugs[:10])
    else:
        result["drugs"] = _dedupe_drugs(existing_drugs)

    return result


# OCR 오인식 dose_unit 보정 맵
_DOSE_UNIT_FIX: dict[str, str] = {
    "점": "정",
    "갭슐": "캡슐",
    "캡술": "캡슐",
    "겝슐": "캡슐",
    "mI": "ml",
    "MI": "ml",
    "ML": "ml",
    "Ml": "ml",
    "적": "방울",
    "drops": "방울",
    "drop": "방울",
}


def _fix_dose_unit(unit: str) -> str:
    """OCR 오인식된 dose_unit을 보정한다."""
    return _DOSE_UNIT_FIX.get(unit.strip(), unit.strip())


_DRUG_NAME_FIX_RE = re.compile(r"[점정][안인]액")


def _fix_drug_name(name: str) -> str:
    """OCR 오인식된 약품명을 보정한다. (점인액/정인액/정안액 → 점안액)"""
    return _DRUG_NAME_FIX_RE.sub("점안액", name)


_KCD_PATTERN = re.compile(
    r"(?:질병분류|상병코드|질병코드|질병\s*분류|상병\s*기호|분류기호|분류)\s{0,10}([1lI][0-9]{3}[0-9A-Z]?|[A-Z][0-9]{2,3}[0-9A-Z]?)"
)
_KCD_LABEL_PATTERN = re.compile(
    r"(?:질병분류|상병코드|질병코드|질병\s*분류|상병\s*기호|분류기호)\s*([1lIA-Z][0-9]{2,4}[0-9A-Z]?)"
)
_KCD_SPACED_PATTERN = re.compile(r"(?<![A-Za-z0-9])([A-Za-z])\s+([0-9])\s+([0-9])\s+([0-9])(?:\s+([0-9]))?(?![A-Za-z])")


def _normalize_kcd(code: str) -> str:
    """OCR 오인식된 KCD 코드 첫 글자를 영문 대문자로 보정한다."""
    if code[0] in ("1", "l"):
        return "I" + code[1:]
    return code


def _extract_kcd_codes(raw_text: str) -> list[str]:
    """raw_text에서 KCD 코드를 추출한다."""
    codes: list[str] = []
    seen: set[str] = set()

    # 라벨 근처 연속 코드
    label_matches = _KCD_LABEL_PATTERN.findall(raw_text)
    if label_matches:
        for c in label_matches:
            n = _normalize_kcd(c)
            if _is_valid_kcd(n) and n not in seen:
                seen.add(n)
                codes.append(n)

    # 일반 패턴
    if not codes:
        for c in _KCD_PATTERN.findall(raw_text):
            n = _normalize_kcd(c)
            if _is_valid_kcd(n) and n not in seen:
                seen.add(n)
                codes.append(n)

    # 칸 분리 형식 (예: J 2 0 9)
    for m in _KCD_SPACED_PATTERN.finditer(raw_text):
        raw_code = "".join(g for g in m.groups() if g is not None)
        n = _normalize_kcd(raw_code)
        if _is_valid_kcd(n) and n not in seen:
            seen.add(n)
            codes.append(n)

    return codes
