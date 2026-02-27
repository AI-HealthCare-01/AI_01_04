from pydantic import BaseModel


class ScanUploadResponse(BaseModel):
    scan_id: int
    status: str


class ScanAnalyzeResponse(BaseModel):
    scan_id: int
    status: str


class ScanResultResponse(BaseModel):
    scan_id: int
    status: str
    analyzed_at: str | None = None
    document_date: str | None = None  # YYYY-MM-DD (처방/진단일)
    diagnosis: str | None = None
    drugs: list[str] = []


class ScanResultUpdateRequest(BaseModel):
    document_date: str | None = None
    diagnosis: str | None = None
    drugs: list[str] = []


class ScanSaveResponse(BaseModel):
    scan_id: int
    saved: bool
