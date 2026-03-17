from pydantic import BaseModel, Field


class DrugEntry(BaseModel):
    """구조화된 약품 정보."""

    name: str
    dose_count: int | None = None  # 1일 복용 횟수
    dose_timing: str | None = None  # 식전/식후/자기전 등
    dose_days: int | None = None  # 투약일수
    dose_amount: str | None = None  # 1회 투여량 (예: "1")
    dose_unit: str | None = None  # 단위 (정, ml 등)


class ScanUploadResponse(BaseModel):
    """스캔 업로드 응답 스키마."""

    scan_id: int
    status: str
    document_type: str | None = None


class ScanAnalyzeResponse(BaseModel):
    """스캔 OCR 분석 시작 응답 스키마."""

    scan_id: int
    status: str
    document_type: str | None = None


class ScanResultResponse(BaseModel):
    """스캔 OCR 분석 결과 응답 스키마."""

    scan_id: int
    status: str
    analyzed_at: str | None = None

    document_type: str | None = None

    document_date: str | None = None
    diagnosis_list: list[str] = Field(default_factory=list)
    clinical_note: str | None = None

    drugs: list[DrugEntry] = Field(default_factory=list)
    unrecognized_drugs: list[str] = Field(default_factory=list)
    raw_text: str | None = None
    error_message: str | None = None


class ScanResultUpdateRequest(BaseModel):
    """스캔 OCR 결과 수정 요청 스키마."""

    document_date: str | None = None
    diagnosis_list: list[str] | None = None
    clinical_note: str | None = None
    drugs: list[DrugEntry] | None = None


class ScanSaveResponse(BaseModel):
    """스캔 결과 저장 응답 스키마."""

    scan_id: int
    saved: bool
    seeded_date: str | None = None
    document_type: str | None = None
    created_prescriptions: list[int] | None = None
    skipped_duplicates: list[str] | None = None
    created_count: int | None = None
    skipped_count: int | None = None
