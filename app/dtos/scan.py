from pydantic import BaseModel, Field  # [CHANGED]


class ScanUploadResponse(BaseModel):
    scan_id: int
    status: str
    document_type: str | None = None  # [ADD]


class ScanAnalyzeResponse(BaseModel):
    scan_id: int
    status: str
    document_type: str | None = None  # [ADD]


class ScanResultResponse(BaseModel):
    scan_id: int
    status: str
    analyzed_at: str | None = None

    document_type: str | None = None  # [ADD]

    document_date: str | None = None  # YYYY-MM-DD (처방/진단일)
    diagnosis: str | None = None
    clinical_note: str | None = None  # [ADD] 진료기록지에서 추출된 진료 내용

    drugs: list[str] = Field(default_factory=list)  # [CHANGED]


class ScanResultUpdateRequest(BaseModel):
    document_date: str | None = None
    diagnosis: str | None = None
    clinical_note: str | None = None  # [ADD]

    drugs: list[str] | None = None


class ScanSaveResponse(BaseModel):
    scan_id: int
    saved: bool
    seeded_date: str | None = None
    created_prescriptions: list[int] | None = None
    skipped_duplicates: list[str] | None = None
    created_count: int | None = None
    skipped_count: int | None = None
