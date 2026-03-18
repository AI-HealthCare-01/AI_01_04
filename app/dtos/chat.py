from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    patient_id: str
    disease_code: str | None = None
    medications: list[str] | None = []
    user_question: str | None = None
    mode: str | None = "medication"
    # 사용자 컨텍스트 자동 주입 여부 (True면 DB에서 자동 조회)
    use_context: bool = True


class ChatResponse(BaseModel):
    chat_answer: str
    report: dict | None = None


class UserContextResponse(BaseModel):
    user_id: int
    diseases: list[dict[str, Any]]
    medications: list[dict[str, Any]]
    scan_summary: dict[str, Any]
    has_diseases: bool
    has_medications: bool
    has_scans: bool


class DeactivateRequest(BaseModel):
    prescription_id: int


class DeactivateResponse(BaseModel):
    success: bool
    message: str
