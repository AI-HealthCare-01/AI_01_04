# raw JSON → 우리 서비스가 쓰는 결과로 변환
import re

DATE_PATTERNS = [
    r"\b(20\d{2})[.\-/](0?[1-9]|1[0-2])[.\-/](0?[1-9]|[12]\d|3[01])\b",  # 2026-02-19 / 2026.02.19
]


def extract_full_text(raw: dict) -> str:
    # 네이버 OCR 일반 응답 구조에서 inferText를 모아 합치는 패턴
    texts: list[str] = []
    images = raw.get("images", [])
    for img in images:
        fields = img.get("fields", [])
        for f in fields:
            t = f.get("inferText")
            if t:
                texts.append(t)
    return " ".join(texts)

def normalize_text(text: str) -> str:
    # 임베딩 전 최소 정제: 공백/개행 정리
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_document_date(text: str) -> str | None:
    for p in DATE_PATTERNS:
        m = re.search(p, text)
        if m:
            y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
            return f"{y}-{mo:02d}-{d:02d}"
    return None


def parse_ocr_result(raw: dict) -> dict:
    full_text = extract_full_text(raw)
    cleaned_text = normalize_text(full_text)
    document_date = extract_document_date(full_text)

    # MVP: diagnosis/drugs는 일단 빈 값으로, 나중에 규칙/모델로 채우기
    # 현재 단계: vector_documents에 바로 연결 가능한 최소 데이터만 제공
    return {
        "document_date": document_date,
        "diagnosis": None,
        "drugs": [],
        "raw_text": cleaned_text,  # 정제 텍스트
        "ocr_raw": raw,            # 원본 응답
        # vector_documents 연결용 최소 메타 (서비스에서 사용)
        "vector_doc": {
            "reference_type": "ocr_scan",
            "reference_id": None,   # scan_id가 생긴 뒤 서비스 레이어에서 주입
            "content": cleaned_text,
        },
    }
