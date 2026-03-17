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
        _client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    return _client


PRESCRIPTION_SYSTEM_PROMPT = """
너는 한국어 처방전 OCR 후처리기다.
반드시 JSON만 반환한다.
키는 정확히 document_date, diagnosis_list, clinical_note, drugs, raw_text, ocr_raw.
- document_date: YYYY-MM-DD 또는 null
- diagnosis_list: 진단명/질병명/질병분류기호(KCD 코드) 배열. 여러 개가 있으면 모두 추출. 예: ["I109 기타 및 상세불명의 원발성 고혈압", "E118 합병증을 동반하지 않은 1형 당뇨병"]. 없으면 []
  OCR 오인식 주의: KCD 코드 첫 글자는 반드시 영문 대문자다. '1', 'l' 로 인식된 경우 'I'로, '0'으로 인식된 경우 'O'로 보정하라. 예: "1219" → "I219", "l109" → "I109"
  한국 첫 방문 질병분류기호 위치: 첫 방문 질병분류기호는 주로 '질병분류', '상병코드', '질병코드' 등의 라벨 근처에 위치한다. 해당 라벨 근처에 영문자+숫자 또는 숫자만으로 된 3~5자리 코드가 있으면 KCD 코드로 간주하고 영문자 보정 후 diagnosis_list에 추가하라.
- clinical_note: null
- drugs:
    1. 문자열 배열. OCR로 인식된 텍스트를 가장 유사한 한국 약물명으로 보정해라. (없으면 [])
    2. 보정 불가능하면 "인식 불가"를 배열에 포함시켜라.
- raw_text: 입력 원문 그대로
- ocr_raw: 입력 원본 JSON 그대로

중요: 질병 코드와 질병명이 여러 줄에 걸쳐 있으면 각각 별도 항목으로 분리하여 diagnosis_list에 추가한다.
예시: "I109 기타 및 상세불명의 원발성 고혈압" 과 "E118 합병증을 동반하지 않은 1형 당뇨병"이 있으면
diagnosis_list: ["I109 기타 및 상세불명의 원발성 고혈압", "E118 합병증을 동반하지 않은 1형 당뇨병"]
"""


MEDICAL_RECORD_SYSTEM_PROMPT = """
너는 한국어 진료기록지 OCR 후처리기다.
반드시 JSON만 반환한다.
키는 정확히 document_date, diagnosis_list, clinical_note, drugs, raw_text, ocr_raw.
- document_date: YYYY-MM-DD 또는 null
- diagnosis_list: 진단명/질병명/질병코드 배열. 여러 개가 있으면 모두 추출. 없으면 []
- clinical_note: 진료 내용, 주증상, 소견, 생활지도, 경과관찰 내용 등을 자연스럽게 정리한 문자열, 없으면 null
- drugs: 문자열 배열 (진료기록지에서 약물명이 명확히 보일 때만 추출, 없으면 [])
- raw_text: 입력 원문 그대로
- ocr_raw: 입력 원본 JSON 그대로

추출 규칙:
1. 진단명/질병코드가 명확하면 diagnosis_list에 넣는다. 여러 개면 모두 추출.
2. 진단명이 없고 증상/소견만 있으면 diagnosis_list는 []로 둔다.
3. symptoms, assessment, plan, instruction, advice 성격의 내용은 clinical_note에 요약한다.
4. 확실하지 않은 내용은 추측하지 말고 null 또는 빈 배열로 둔다.
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
        "document_type": document_type,
        "raw_text": raw_text,
        "parser_hints": {
            "candidate_dates": parser_hints.get("candidate_dates", []),
            "candidate_diagnosis_codes": parser_hints.get("candidate_diagnosis_codes", []),
            "candidate_drugs": parser_hints.get("candidate_drugs", []),
        },
    }

    response = await client.responses.create(
        model=config.OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "다음 데이터를 스키마에 맞춰 정규화하여 json으로 반환:\n"
                    f"{json.dumps(user_payload, ensure_ascii=False)}\n"
                    "반드시 JSON 객체만 반환하고, raw_text와 ocr_raw는 생략해도 된다."
                ),
            },
        ],
        text={"format": {"type": "json_object"}},
    )

    text = response.output_text
    result = _extract_json_object(text)

    result.setdefault("document_date", None)
    result.setdefault("diagnosis_list", [])
    result.setdefault("clinical_note", None)
    result.setdefault("drugs", [])
    result.setdefault("raw_text", raw_text)
    result["ocr_raw"] = ocr_raw  # LLM 응답과 무관하게 원본 그대로 저장

    if not isinstance(result["diagnosis_list"], list):
        result["diagnosis_list"] = []
    if not isinstance(result["drugs"], list):
        result["drugs"] = []

    result = _merge_parser_hints(result, parser_hints)

    result["unrecognized_drugs"] = [d for d in result["drugs"] if d == "인식 불가"]
    result["drugs"] = [d for d in result["drugs"] if d != "인식 불가"]

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


def _merge_parser_hints(result: dict, parser_hints: dict) -> dict:
    """AI 결과가 빈약할 때 parser 후보를 최소한으로 보완한다."""
    candidate_codes = [
        item for item in parser_hints.get("candidate_diagnosis_codes", []) if isinstance(item, str) and item.strip()
    ]
    candidate_drugs = [
        item for item in parser_hints.get("candidate_drugs", []) if isinstance(item, str) and item.strip()
    ]

    diagnosis_list = [item for item in result.get("diagnosis_list", []) if isinstance(item, str) and item.strip()]
    drugs = [item for item in result.get("drugs", []) if isinstance(item, str) and item.strip()]

    if not diagnosis_list and candidate_codes:
        result["diagnosis_list"] = _dedupe_keep_order(candidate_codes[:5])
    else:
        result["diagnosis_list"] = _dedupe_keep_order(diagnosis_list)

    if not drugs and candidate_drugs:
        result["drugs"] = _dedupe_keep_order(candidate_drugs[:10])
    else:
        result["drugs"] = _dedupe_keep_order(drugs)

    return result


_KCD_PATTERN = re.compile(
    r"(?:질병분류|상병코드|질병코드|질병\s*분류|상병\s*기호|분류기호|분류)\s{0,10}([1lI][0-9]{3}[0-9A-Z]?|[A-Z][0-9]{2,3}[0-9A-Z]?)"
)
_KCD_LABEL_PATTERN = re.compile(
    r"(?:질병분류|상병코드|질병코드|질병\s*분류|상병\s*기호|분류기호)\s*([1lIA-Z][0-9]{2,4}[0-9A-Z]?)"
)


def _normalize_kcd(code: str) -> str:
    """OCR 오인식된 KCD 코드 첫 글자를 영문 대문자로 보정한다."""
    if code[0] in ("1", "l"):
        return "I" + code[1:]
    return code


def _extract_kcd_codes(raw_text: str) -> list[str]:
    """raw_text에서 KCD 코드를 추출한다."""
    label_matches = _KCD_LABEL_PATTERN.findall(raw_text)
    if label_matches:
        return [_normalize_kcd(c) for c in label_matches]
    return [normalized for c in _KCD_PATTERN.findall(raw_text) if (normalized := _normalize_kcd(c))[0].isalpha()]
