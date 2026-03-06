import json

from openai import OpenAI  # type: ignore[import-not-found]

from app.core import config

client = OpenAI(api_key=config.OPENAI_API_KEY)


PRESCRIPTION_SYSTEM_PROMPT = """
너는 한국어 처방전 OCR 후처리기다.  # [CHANGED]
반드시 JSON만 반환한다.
키는 정확히 document_date, diagnosis, clinical_note, drugs, raw_text, ocr_raw.
- document_date: YYYY-MM-DD 또는 null
- diagnosis: 문자열 또는 null
- clinical_note: null
- drugs: 문자열 배열 (없으면 [])
- raw_text: 입력 원문 그대로
- ocr_raw: 입력 원본 JSON 그대로
"""  # [CHANGED]


MEDICAL_RECORD_SYSTEM_PROMPT = """
너는 한국어 진료기록지 OCR 후처리기다.  # [ADD]
반드시 JSON만 반환한다.
키는 정확히 document_date, diagnosis, clinical_note, drugs, raw_text, ocr_raw.
- document_date: YYYY-MM-DD 또는 null
- diagnosis: 진단명/질병명/질병코드 기반으로 추정 가능한 경우 문자열, 없으면 null
- clinical_note: 진료 내용, 주증상, 소견, 생활지도, 경과관찰 내용 등을 자연스럽게 정리한 문자열, 없으면 null
- drugs: 문자열 배열 (진료기록지에서 약물명이 명확히 보일 때만 추출, 없으면 [])
- raw_text: 입력 원문 그대로
- ocr_raw: 입력 원본 JSON 그대로

추출 규칙:
1. 진단명/질병코드가 명확하면 diagnosis에 넣는다.
2. 진단명이 없고 증상/소견만 있으면 diagnosis는 null로 둔다.
3. symptoms, assessment, plan, instruction, advice 성격의 내용은 clinical_note에 요약한다.
4. 확실하지 않은 내용은 추측하지 말고 null 또는 빈 배열로 둔다.
"""  # [ADD]


def _get_system_prompt(document_type: str) -> str:  # [ADD]
    if document_type == "medical_record":
        return MEDICAL_RECORD_SYSTEM_PROMPT
    return PRESCRIPTION_SYSTEM_PROMPT


def ai_postprocess(
    raw_text: str,
    ocr_raw: dict,
    document_type: str = "prescription",  # [ADD]
) -> dict:
    system_prompt = _get_system_prompt(document_type)  # [ADD]

    user_payload = {
        "document_type": document_type,  # [ADD]
        "raw_text": raw_text,
        "ocr_raw": ocr_raw,
    }

    res = client.responses.create(
        model=config.OPENAI_MODEL,
        input=[
            {"role": "system", "content": system_prompt},  # [CHANGED]
            {
                "role": "user",
                "content": f"다음 데이터를 스키마에 맞춰 정규화:\n{json.dumps(user_payload, ensure_ascii=False)}",
            },
        ],
        text={"format": {"type": "json_object"}},
    )

    text = res.output_text
    result = json.loads(text)

    # [ADD] 응답 스키마 최소 보정
    if not isinstance(result, dict):
        raise ValueError("AI postprocess result must be a dict")

    result.setdefault("document_date", None)
    result.setdefault("diagnosis", None)
    result.setdefault("clinical_note", None)
    result.setdefault("drugs", [])
    result.setdefault("raw_text", raw_text)
    result.setdefault("ocr_raw", ocr_raw)

    if not isinstance(result["drugs"], list):
        result["drugs"] = []

    return result
