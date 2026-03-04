import json

from openai import OpenAI  # type: ignore[import-not-found]

from app.core import config

client = OpenAI(api_key=config.OPENAI_API_KEY)


SYSTEM_PROMPT = """
너는 한국어 처방전/ORM 후처리기다.
반드시 JSON만 반환한다.
키는 정확히 document_date, diagnosis, drugs, raw_text, ocr_raw.
- document_date: YYYY-MM-DD 또는 null
- diagnosis: 문자열 또는 null
- drugs: 문자열 배열 (없으면 [])
- raw_text: 입력 원문 그대로
- ocr_raw: 입력 원본 JSON 그대로
"""


def ai_postprocess(raw_text: str, ocr_raw: dict) -> dict:
    user_payload = {
        "raw_text": raw_text,
        "ocr_raw": ocr_raw,
    }

    res = client.responses.create(
        model=config.OPENAI_MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"다음 데이터를 스키마에 맞춰 정규화:\n{json.dumps(user_payload, ensure_ascii=False)}",
            },
        ],
        text={"format": {"type": "json_object"}},
    )

    text = res.output_text
    return json.loads(text)
