from pydantic import BaseModel, Field  # [CHANGED]


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
    diagnosis: str | None = None
    clinical_note: str | None = None

    drugs: list[str] = Field(default_factory=list)


class ScanResultUpdateRequest(BaseModel):
    """스캔 OCR 결과 수정 요청 스키마."""

    document_date: str | None = None
    diagnosis: str | None = None
    clinical_note: str | None = None

    drugs: list[str] | None = None


class ScanSaveResponse(BaseModel):
    """스캔 결과 저장 응답 스키마."""

    scan_id: int
    saved: bool
    seeded_date: str | None = None
    created_prescriptions: list[int] | None = None
    skipped_duplicates: list[str] | None = None
    created_count: int | None = None
    skipped_count: int | None = None
