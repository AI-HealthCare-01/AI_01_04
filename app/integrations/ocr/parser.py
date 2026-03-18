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
_DRUG_LABEL_RE = re.compile(r"(?:약품명|약명|처방약|투약명|복용약)\s*[:：]?\s*([^\n\r]+)")
_SPACED_KCD_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z1l])\s+([0-9])\s+([0-9])\s+([0-9])(?:\s+([0-9]))?(?![A-Za-z])"
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


def _field_mid_y(field: dict[str, Any]) -> float | None:
    """필드의 bounding box 중앙 y좌표를 반환한다."""
    bp = field.get("boundingPoly", {})
    vertices = bp.get("vertices") or []
    if not vertices:
        return None
    ys = [v.get("y", 0) for v in vertices if isinstance(v, dict)]
    return (min(ys) + max(ys)) / 2 if ys else None


_DIAG_LABEL_CHARS = {"질병", "분류", "기호", "상병", "코드"}
_ROW_Y_TOLERANCE = 15


def _extract_diagnosis_codes_from_fields(fields: list[dict[str, Any]]) -> list[str]:
    """OCR 필드의 좌표를 이용해 질병분류 칸 영역의 코드를 행별로 추출한다.

    처방전의 질병분류기호 칸은 각 글자가 별도 칸에 있고, OCR이 열 우선으로
    읽어 두 줄의 코드가 섞이는 문제를 y좌표 기반 행 분리로 해결한다.
    """
    # 1) 질병/분류/기호 라벨 위치 탐색
    label_indices: list[int] = []
    for i, f in enumerate(fields):
        t = (f.get("inferText") or "").strip()
        if t in _DIAG_LABEL_CHARS:
            label_indices.append(i)
    if not label_indices:
        return []

    # 2) 라벨 직후의 단일 영숫자 필드를 수집
    start = label_indices[-1] + 1
    single_chars: list[tuple[float, float, str]] = []  # (mid_y, x, char)
    for i in range(start, min(start + 20, len(fields))):
        f = fields[i]
        t = (f.get("inferText") or "").strip()
        if len(t) != 1 or not t.isalnum():
            break
        mid_y = _field_mid_y(f)
        bp = f.get("boundingPoly", {})
        vertices = bp.get("vertices") or []
        x = vertices[0].get("x", 0) if vertices else 0
        if mid_y is not None:
            single_chars.append((mid_y, x, t))

    if not single_chars:
        return []

    # 3) y좌표 기준으로 행 그룹핑
    single_chars.sort(key=lambda c: (c[0], c[1]))
    rows: list[list[tuple[float, float, str]]] = []
    for char_info in single_chars:
        placed = False
        for row in rows:
            if abs(row[0][0] - char_info[0]) <= _ROW_Y_TOLERANCE:
                row.append(char_info)
                placed = True
                break
        if not placed:
            rows.append([char_info])

    # 4) 각 행을 x좌표 순으로 정렬 후 병합하여 KCD 코드 후보 생성
    codes: list[str] = []
    for row in rows:
        row.sort(key=lambda c: c[1])
        merged = "".join(c[2] for c in row)
        normalized = _normalize_kcd_code(merged)
        if re.fullmatch(r"[A-Z]\d{2,4}[0-9A-Z]?", normalized):
            codes.append(normalized)
    return codes


def _merge_single_char_fields(fields: list[dict[str, Any]]) -> list[str]:
    """인접한 단일 문자 필드를 하나의 토큰으로 병합한다.

    처방전의 칸 입력 형식(예: I / 1 / 0 / 9)에서 OCR이 각 칸을
    별도 필드로 인식하는 경우를 처리한다.
    """
    result: list[str] = []
    buf: list[str] = []
    for field in fields:
        t = field.get("inferText")
        if not isinstance(t, str) or not t.strip():
            if buf:
                result.append("".join(buf))
                buf = []
            continue
        stripped = t.strip()
        if len(stripped) == 1 and (stripped.isalnum()):
            buf.append(stripped)
        else:
            if buf:
                result.append("".join(buf))
                buf = []
            result.append(stripped)
    if buf:
        result.append("".join(buf))
    return result


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
        fields = img.get("fields", []) or []
        # 순서 기반 단일 문자 병합 결과 추가
        merged = _merge_single_char_fields(fields)
        texts.extend(merged)
        # 원본 필드도 추가 (공백 분리 패턴 매칭용)
        for field in fields:
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


def _extract_spaced_kcd_codes(text: str) -> list[str]:
    """공백으로 분리된 칸 입력 형식의 KCD 코드를 추출한다.

    예: 'I 1 0 9' → 'I109', 'E 1 1 8' → 'E118'
    """
    codes: list[str] = []
    seen: set[str] = set()
    for m in _SPACED_KCD_RE.finditer(text):
        raw = "".join(g for g in m.groups() if g is not None)
        value = _normalize_kcd_code(raw)
        if re.fullmatch(r"[A-Z]\d{2,4}[0-9A-Z]?", value) and value not in seen:
            seen.add(value)
            codes.append(value)
    return codes


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

    # 칸 분리 형식 (예: I 1 0 9) 추출
    for value in _extract_spaced_kcd_codes(text):
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
    drug_candidates = extract_drug_candidates(raw, full_text)

    # 좌표 기반 행 분리 추출을 우선 시도
    coord_codes: list[str] = []
    for img in raw.get("images", []) or []:
        coord_codes.extend(_extract_diagnosis_codes_from_fields(img.get("fields", []) or []))

    if coord_codes:
        kcd_codes = coord_codes
    else:
        kcd_codes = extract_kcd_codes(full_text)

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
