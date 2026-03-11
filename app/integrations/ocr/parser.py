# raw JSON → 우리 서비스가 쓰는 결과로 변환
# /Users/admin/Desktop/1/AI_01_04/app/integrations/ocr/parser.py
import re
from typing import Any

DATE_PATTERNS = [
    r"\b(20\d{2})[.\-/](0?[1-9]|1[0-2])[.\-/](0?[1-9]|[12]\d|3[01])\b",
]

_WS_RE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    """
    연속된 공백을 단일 공백으로 정규화.

    Args:
        text (str): 정규화할 텍스트.

    Returns:
        str: 정규화된 텍스트.
    """
    return _WS_RE.sub(" ", text).strip()


def extract_full_text(raw: dict[str, Any]) -> str:
    """
    OCR raw JSON에서 전체 텍스트 추출.

    Args:
        raw (dict[str, Any]): 네이버 OCR API raw 응답.

    Returns:
        str: 전체 텍스트 연결 문자열.
    """
    texts: list[str] = []

    for img in raw.get("images", []) or []:
        for field in img.get("fields", []) or []:
            t = field.get("inferText")
            if isinstance(t, str) and t.strip():
                texts.append(t)

        for line in img.get("lines", []) or []:
            t = line.get("text")
            if isinstance(t, str) and t.strip():
                texts.append(t)

        parsed_text = img.get("parsedText")
        if isinstance(parsed_text, str) and parsed_text.strip():
            texts.append(parsed_text)

        infer_text = img.get("inferText")
        if isinstance(infer_text, str) and infer_text.strip():
            texts.append(infer_text)

    return _normalize_text(" ".join(texts))


def extract_document_date(text: str) -> str | None:
    """
    텍스트에서 YYYY-MM-DD 형식 날짜 추출.

    Args:
        text (str): 날짜를 추출할 원본 텍스트.

    Returns:
        str | None: 추출된 YYYY-MM-DD 날짜 문자열, 없으면 None.
    """
    for pattern in DATE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
            return f"{y}-{mo:02d}-{d:02d}"
    return None


def parse_ocr_result(raw: dict[str, Any]) -> dict[str, Any]:
    """
    OCR raw JSON을 서비스 표준 결과로 변환.

    Args:
        raw (dict[str, Any]): 네이버 OCR API raw 응답.

    Returns:
        dict[str, Any]: document_date, diagnosis, drugs, raw_text, ocr_raw 포함 딕셔너리.
    """
    full_text = extract_full_text(raw)
    document_date = extract_document_date(full_text)

    return {
        "document_date": document_date,
        "diagnosis": None,
        "drugs": [],
        "raw_text": full_text if full_text else None,
        "ocr_raw": raw,
    }
