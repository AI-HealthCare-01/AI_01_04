"""
스캔 모델 (ERD: scans)

- 의료문서 OCR 분석 결과 저장
- document_type: prescription(처방전) / medical_record(진료기록지)
- 상태 흐름: uploaded → processing → done → updated → saved / failed
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

if TYPE_CHECKING:
    from app.models.users import User


class Scan(models.Model):
    """
    의료문서 스캔 도메인 모델 (ERD: scans).

    Attributes:
        document_type: ``prescription`` (처방전) | ``medical_record`` (진료기록지).
        status: uploaded → processing → done → updated → saved | failed.
        drugs: OCR 파싱된 약물명 목록 (JSON 배열).
        ocr_raw: Naver OCR 원본 응답 (JSON).
        clinical_note: 진료기록지에서 추출한 진료 내용.
    """

    id = fields.IntField(pk=True)

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="scans",
    )
    user_id: int

    status = fields.CharField(max_length=30, default="uploaded")
    analyzed_at = fields.DatetimeField(null=True)

    document_type = fields.CharField(max_length=30, default="prescription")  # [ADD]

    document_date = fields.CharField(max_length=10, null=True)
    diagnosis = fields.TextField(null=True)  # 하위호환: 단일 진단명 (레거시)
    diagnosis_list: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]
    clinical_note = fields.TextField(null=True)  # [ADD]
    error_message = fields.TextField(null=True)

    drugs: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]
    unrecognized_drugs: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]

    raw_text = fields.TextField(null=True)
    ocr_raw: dict = fields.JSONField(null=True)  # type: ignore[assignment]

    file_path = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "scans"
        indexes = (
            ("user_id", "id"),
            ("user_id", "created_at"),
            ("user_id", "document_type"),  # [ADD]
        )
