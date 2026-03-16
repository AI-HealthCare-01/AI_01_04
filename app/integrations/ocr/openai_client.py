from __future__ import annotations

import json

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


async def ai_postprocess(
    raw_text: str,
    ocr_raw: dict,
    document_type: str = "prescription",
) -> dict:
    """OCR 결과를 OpenAI로 후처리하여 구조화된 dict를 반환한다."""
    client = get_openai_client()
    system_prompt = _get_system_prompt(document_type)

    user_payload = {
        "document_type": document_type,
        "raw_text": raw_text,
        "ocr_raw": ocr_raw,
    }

    response = await client.responses.create(
        model=config.OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"다음 데이터를 스키마에 맞춰 정규화하여 json으로 반환:\n{json.dumps(user_payload, ensure_ascii=False)}",
            },
        ],
        text={"format": {"type": "json_object"}},
    )

    text = response.output_text
    result = json.loads(text)

    if not isinstance(result, dict):
        raise ValueError("AI postprocess result must be a dict")

    result.setdefault("document_date", None)
    result.setdefault("diagnosis_list", [])
    result.setdefault("clinical_note", None)
    result.setdefault("drugs", [])
    result.setdefault("raw_text", raw_text)
    result.setdefault("ocr_raw", ocr_raw)

    if not isinstance(result["diagnosis_list"], list):
        result["diagnosis_list"] = []
    if not isinstance(result["drugs"], list):
        result["drugs"] = []

    result["unrecognized_drugs"] = [d for d in result["drugs"] if d == "인식 불가"]
    result["drugs"] = [d for d in result["drugs"] if d != "인식 불가"]

    return result
