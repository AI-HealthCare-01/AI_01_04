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

# 여러 공백, 개행, 탭을 하나의 공백으로 정규화
_WS_RE = re.compile(r"\s+")

# 일반적인 KCD 코드 후보
_KCD_CODE_RE = re.compile(r"\b([A-Za-z1l]\d{2,4}[0-9A-Z]?)\b")

# 질병분류/상병코드 등의 라벨 바로 뒤에 오는 코드 후보
_KCD_LABEL_RE = re.compile(
    r"(?:질병분류|상병코드|질병코드|질병\s*분류|상병\s*기호|분류기호)\s*[:：]?\s*([A-Za-z1l]\d{2,4}[0-9A-Z]?)"
)

# 약품명 형태 후보
_DRUG_FORM_RE = re.compile(r"[가-힣A-Za-z0-9\-]{2,40}(?:정|정\d+mg|캡슐|시럽|액|주|산|연질캡슐|현탁액|크림|겔|패취)")

# "약품명: xxx" 같은 라벨형 텍스트 후보
_DRUG_LABEL_RE = re.compile(r"(?:약품명|약명|처방약|투약명|복용약)\s*[:：]?\s*([^\n\r]+)")

# 칸 분리 OCR 결과용 KCD 패턴
# 예: "I 1 0 9", "E 1 1 8"
_SPACED_KCD_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z1l])\s+([0-9])\s+([0-9])\s+([0-9])(?:\s+([0-9]))?(?![A-Za-z])")

# 약품 후보에서 제거할 노이즈 키워드
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

# 처방전 질병분류 라벨을 이루는 문자 후보
_DIAG_LABEL_CHARS = {"질병", "분류", "기호", "상병", "코드"}

# y좌표 차이가 이 값 이하이면 같은 행으로 본다
_ROW_Y_TOLERANCE = 12

# 질병분류 라벨 기준 코드 영역 탐색 오프셋 (px)
_REGION_PAD_LEFT = 10
_REGION_PAD_RIGHT = 220
_REGION_PAD_TOP = 30
_REGION_PAD_BOTTOM = 110


def _normalize_text(text: str) -> str:
    """연속된 공백을 단일 공백으로 정규화한다."""
    return _WS_RE.sub(" ", text).strip()


def _normalize_kcd_code(code: str) -> str:
    """OCR 오인식 가능성이 큰 KCD 코드 첫 글자를 보정한다.

    예:
    - 1109 -> I109
    - L109 -> I109
    """
    cleaned = code.strip().upper()
    if not cleaned:
        return cleaned
    if cleaned[0] in {"1", "L"}:
        return "I" + cleaned[1:]
    return cleaned


def _field_bounds(field: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """OCR field의 bounding box를 (min_x, min_y, max_x, max_y)로 반환한다."""
    bp = field.get("boundingPoly", {})
    vertices = bp.get("vertices") or []
    if not vertices:
        return None

    xs = [v.get("x", 0) for v in vertices if isinstance(v, dict)]
    ys = [v.get("y", 0) for v in vertices if isinstance(v, dict)]
    if not xs or not ys:
        return None

    return min(xs), min(ys), max(xs), max(ys)


def _compute_code_region(
    label_boxes: list[tuple[float, float, float, float]],
) -> tuple[float, float, float, float]:
    """질병분류 라벨 박스들로부터 코드 탐색 영역 (left, right, top, bottom)을 계산한다."""
    label_min_y = min(box[1] for box in label_boxes)
    label_max_x = max(box[2] for box in label_boxes)
    label_max_y = max(box[3] for box in label_boxes)

    return (
        label_max_x - _REGION_PAD_LEFT,
        label_max_x + _REGION_PAD_RIGHT,
        label_min_y - _REGION_PAD_TOP,
        label_max_y + _REGION_PAD_BOTTOM,
    )


def _collect_single_chars(
    fields: list[dict[str, Any]],
    region: tuple[float, float, float, float],
) -> list[tuple[float, float, str]]:
    """코드 영역 안의 단일 ASCII 영숫자 문자를 (mid_y, mid_x, text)로 수집한다."""
    region_left, region_right, region_top, region_bottom = region
    result: list[tuple[float, float, str]] = []

    for field in fields:
        text = (field.get("inferText") or "").strip()
        if len(text) != 1 or not text.isascii() or not text.isalnum():
            continue

        bounds = _field_bounds(field)
        if bounds is None:
            continue

        min_x, min_y, max_x, max_y = bounds
        mid_x = (min_x + max_x) / 2
        mid_y = (min_y + max_y) / 2

        if region_left <= mid_x <= region_right and region_top <= mid_y <= region_bottom:
            result.append((mid_y, mid_x, text))

    return result


def _group_chars_into_codes(
    single_chars: list[tuple[float, float, str]],
) -> list[str]:
    """단일 문자들을 y좌표 기준 행으로 묶고 x좌표 순으로 이어붙여 KCD 코드를 생성한다."""
    single_chars.sort(key=lambda item: (item[0], item[1]))

    rows: list[list[tuple[float, float, str]]] = []
    for item in single_chars:
        placed = False
        for row in rows:
            if abs(row[0][0] - item[0]) <= _ROW_Y_TOLERANCE:
                row.append(item)
                placed = True
                break
        if not placed:
            rows.append([item])

    codes: list[str] = []
    seen: set[str] = set()

    for row in rows:
        row.sort(key=lambda item: item[1])
        merged = "".join(cell[2] for cell in row)
        normalized = _normalize_kcd_code(merged)

        if re.fullmatch(r"[A-Z]\d{3,4}[0-9A-Z]?", normalized):
            if normalized not in seen:
                seen.add(normalized)
                codes.append(normalized)

    return codes


def _extract_diagnosis_codes_from_fields(fields: list[dict[str, Any]]) -> list[str]:
    """질병분류기호 칸을 좌표 기반으로 찾아 행별 코드 후보를 추출한다."""
    label_fields = [f for f in fields if (f.get("inferText") or "").strip() in _DIAG_LABEL_CHARS]
    if not label_fields:
        return []

    label_boxes: list[tuple[float, float, float, float]] = [
        box for box in (_field_bounds(f) for f in label_fields) if box is not None
    ]
    if not label_boxes:
        return []

    region = _compute_code_region(label_boxes)
    single_chars = _collect_single_chars(fields, region)
    if not single_chars:
        return []

    return _group_chars_into_codes(single_chars)


def _merge_single_char_fields(fields: list[dict[str, Any]]) -> list[str]:
    """인접한 단일 문자 필드를 하나의 토큰으로 병합한다.

    예:
    - I / 1 / 0 / 9 -> I109

    다만 OCR field 순서가 완전히 신뢰되지는 않으므로,
    이 결과는 참고용 full_text 생성에만 사용하고
    질병코드 추출의 최우선 근거로 쓰지는 않는다.
    """
    result: list[str] = []
    buf: list[str] = []

    for field in fields:
        text = field.get("inferText")
        if not isinstance(text, str) or not text.strip():
            if buf:
                result.append("".join(buf))
                buf = []
            continue

        stripped = text.strip()
        if len(stripped) == 1 and stripped.isascii() and stripped.isalnum():
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
    """OCR raw JSON에서 전체 텍스트를 최대한 모아 하나의 문자열로 만든다."""
    texts: list[str] = []

    for img in raw.get("images", []) or []:
        fields = img.get("fields", []) or []

        # 순서 기반 단일 문자 병합 결과 추가
        merged = _merge_single_char_fields(fields)
        texts.extend(merged)

        # 원본 field 텍스트도 추가
        for field in fields:
            text = field.get("inferText")
            if isinstance(text, str) and text.strip():
                texts.append(text)

        # line 단위 텍스트 추가
        for line in img.get("lines", []) or []:
            text = line.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text)

        # parsedText, inferText가 있으면 추가
        parsed_text = img.get("parsedText")
        if isinstance(parsed_text, str) and parsed_text.strip():
            texts.append(parsed_text)

        infer_text = img.get("inferText")
        if isinstance(infer_text, str) and infer_text.strip():
            texts.append(infer_text)

    return _normalize_text(" ".join(texts))


def extract_document_date(text: str) -> str | None:
    """텍스트에서 YYYY-MM-DD 형식 날짜를 추출한다."""
    for pattern in DATE_LABEL_PATTERNS + DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            year, month, day = match.group(1), int(match.group(2)), int(match.group(3))
            return f"{year}-{month:02d}-{day:02d}"
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

    예:
    - I 1 0 9 -> I109
    - E 1 1 8 -> E118
    """
    codes: list[str] = []
    seen: set[str] = set()

    for match in _SPACED_KCD_RE.finditer(text):
        raw = "".join(group for group in match.groups() if group is not None)
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

    for value in _extract_spaced_kcd_codes(text):
        if value not in seen:
            seen.add(value)
            codes.append(value)

    return codes


def _clean_drug_candidate(value: str) -> str | None:
    """약품 후보 문자열을 정리하고 노이즈면 제거한다."""
    cleaned = _normalize_text(value)
    if not cleaned or any(keyword in cleaned for keyword in _NOISE_KEYWORDS):
        return None
    return cleaned


def _append_unique(items: list[str], seen: set[str], value: str | None) -> None:
    """중복되지 않는 값만 리스트에 추가한다."""
    if not value or value in seen:
        return
    seen.add(value)
    items.append(value)


def _extract_labeled_drug_candidates(text: str) -> list[str]:
    """라벨형 텍스트에서 약품 후보를 추출한다."""
    items: list[str] = []
    seen: set[str] = set()

    for match in re.finditer(_DRUG_LABEL_RE, text):
        segment = match.group(1)
        for token in re.split(r"[,\s/]+", segment):
            _append_unique(items, seen, _clean_drug_candidate(token))

    return items


def _extract_form_drug_candidates(text: str) -> list[str]:
    """일반적인 약품명 패턴으로 약품 후보를 추출한다."""
    items: list[str] = []
    seen: set[str] = set()

    for token in _DRUG_FORM_RE.findall(text):
        _append_unique(items, seen, _clean_drug_candidate(token))

    return items


def _extract_field_drug_candidates(raw: dict[str, Any]) -> list[str]:
    """OCR field 단위 텍스트에서 약품명 후보를 추출한다."""
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
    """OCR 결과에서 약품명 후보를 수집한다."""
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
    """OCR raw JSON에서 1차 구조화 결과를 생성한다.

    우선순위:
    1. 좌표 기반 질병코드 추출
    2. full_text 기반 정규식 추출
    """
    full_text = extract_full_text(raw)
    document_date = extract_document_date(full_text)
    partial_dates = extract_partial_document_dates(full_text)
    drug_candidates = extract_drug_candidates(raw, full_text)

    coord_codes: list[str] = []
    seen_coord_codes: set[str] = set()

    for img in raw.get("images", []) or []:
        extracted = _extract_diagnosis_codes_from_fields(img.get("fields", []) or [])
        for code in extracted:
            if code not in seen_coord_codes:
                seen_coord_codes.add(code)
                coord_codes.append(code)

    regex_codes = extract_kcd_codes(full_text)

    kcd_codes = coord_codes if coord_codes else regex_codes

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
