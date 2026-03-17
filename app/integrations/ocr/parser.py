"""OCR raw에서 전체 텍스트와 구조화 후보를 1차 추출한다."""

import re
from typing import Any

DATE_PATTERNS = [
    r"\b(20\d{2})[.\-/](1[0-2]|0?[1-9])[.\-/](3[01]|[12]\d|0?[1-9])\b",
    r"\b(20\d{2})년\s*(1[0-2]|0?[1-9])월\s*(3[01]|[12]\d|0?[1-9])일\b",
]
PARTIAL_DATE_PATTERNS = [
    r"\b(20\d{2})[.\-/](1[0-2]|0?[1-9])\b",
    r"\b(20\d{2})년\s*(1[0-2]|0?[1-9])월\b",
]
DATE_LABEL_PATTERNS = [
    r"(?:처방일|조제일|진료일|작성일|발행일)\s*[:：]?\s*(20\d{2})[.\-/년\s]+(1[0-2]|0?[1-9])[.\-/월\s]+(3[01]|[12]\d|0?[1-9])",
]

_WS_RE = re.compile(r"\s+")
_KCD_CODE_RE = re.compile(r"\b([A-Za-z1l]\d{2,4}[0-9A-Z]?)\b")
_KCD_LABEL_RE = re.compile(
    r"(?:질병분류|상병코드|질병코드|질병\s*분류|상병\s*기호|분류기호)\s*[:：]?\s*([A-Za-z1l]\d{2,4}[0-9A-Z]?)"
)
_DRUG_FORM_RE = re.compile(r"[가-힣A-Za-z0-9\-]{2,40}(?:정|정\d+mg|캡슐|시럽|액|주|산|연질캡슐|현탁액|크림|겔|패취)")
_DRUG_LABEL_RE = re.compile(
    r"(?:약품명|약명|처방약|투약명|복용약)\s*[:：]?\s*([^\n\r]+)"
)
_NOISE_KEYWORDS = (
    "주민",
    "보험",
    "전화",
    "주소",
    "병원",
    "의원",
    "약국",
    "팩스",
    "용법",
    "용량",
    "횟수",
    "번호",
)


def _normalize_text(text: str) -> str:
    """
    연속된 공백을 단일 공백으로 정규화.

    Args:
        text (str): 정규화할 텍스트.

    Returns:
        str: 정규화된 텍스트.
    """
    return _WS_RE.sub(" ", text).strip()


def _normalize_kcd_code(code: str) -> str:
    """OCR 오인식 가능성이 큰 KCD 코드 첫 글자를 보정한다."""
    cleaned = code.strip().upper()
    if not cleaned:
        return cleaned
    if cleaned[0] in {"1", "L"}:
        return "I" + cleaned[1:]
    return cleaned


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
    for pattern in DATE_LABEL_PATTERNS + DATE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
            return f"{y}-{mo:02d}-{d:02d}"
    return None


def extract_partial_document_dates(text: str) -> list[str]:
    """텍스트에서 월까지만 있는 날짜 후보를 YYYY-MM 형식으로 추출한다."""
    candidates: list[str] = []
    seen: set[str] = set()
    for pattern in PARTIAL_DATE_PATTERNS:
        for match in re.finditer(pattern, text):
            value = f"{match.group(1)}-{int(match.group(2)):02d}"
            if value not in seen:
                seen.add(value)
                candidates.append(value)
    return candidates


def extract_kcd_codes(text: str) -> list[str]:
    """텍스트에서 KCD/ICD 형태의 질병코드 후보를 추출한다."""
    codes: list[str] = []
    seen: set[str] = set()

    for pattern in (_KCD_LABEL_RE, _KCD_CODE_RE):
        for match in re.finditer(pattern, text):
            value = _normalize_kcd_code(match.group(1))
            if not re.fullmatch(r"[A-Z]\d{2,4}[0-9A-Z]?", value):
                continue
            if value not in seen:
                seen.add(value)
                codes.append(value)

    return codes


def _clean_drug_candidate(value: str) -> str | None:
    cleaned = _normalize_text(value)
    if not cleaned or any(keyword in cleaned for keyword in _NOISE_KEYWORDS):
        return None
    return cleaned


def _append_unique(items: list[str], seen: set[str], value: str | None) -> None:
    if not value or value in seen:
        return
    seen.add(value)
    items.append(value)


def _extract_labeled_drug_candidates(text: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(_DRUG_LABEL_RE, text):
        segment = match.group(1)
        for token in re.split(r"[,\s/]+", segment):
            _append_unique(items, seen, _clean_drug_candidate(token))
    return items


def _extract_form_drug_candidates(text: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for token in _DRUG_FORM_RE.findall(text):
        _append_unique(items, seen, _clean_drug_candidate(token))
    return items


def _extract_field_drug_candidates(raw: dict[str, Any]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for img in raw.get("images", []) or []:
        for field in img.get("fields", []) or []:
            infer_text = field.get("inferText")
            if not isinstance(infer_text, str):
                continue
            cleaned = _clean_drug_candidate(infer_text)
            if cleaned and _DRUG_FORM_RE.fullmatch(cleaned):
                _append_unique(items, seen, cleaned)
    return items


def extract_drug_candidates(raw: dict[str, Any], text: str) -> list[str]:
    """OCR 결과에서 약품명 후보를 추출한다."""
    candidates: list[str] = []
    seen: set[str] = set()
    for group in (
        _extract_labeled_drug_candidates(text),
        _extract_form_drug_candidates(text),
        _extract_field_drug_candidates(raw),
    ):
        for item in group:
            _append_unique(candidates, seen, item)

    return candidates


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
    partial_dates = extract_partial_document_dates(full_text)
    kcd_codes = extract_kcd_codes(full_text)
    drug_candidates = extract_drug_candidates(raw, full_text)

    return {
        "document_date": document_date,
        "diagnosis": None,
        "drugs": [],
        "candidate_dates": partial_dates,
        "candidate_diagnosis_codes": kcd_codes,
        "candidate_drugs": drug_candidates,
        "raw_text": full_text if full_text else None,
        "ocr_raw": raw,
    }
