from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

if TYPE_CHECKING:
    from app.models.users import User


class Scan(models.Model):
    """
    처방전 스캔 도메인 모델

    - status: uploaded → processing → done → updated → saved / failed
    - drugs: OCR 파싱된 약물명 목록 (JSON 배열)
    - ocr_raw: Naver OCR 원본 응답 (JSON)
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

    document_date = fields.CharField(max_length=10, null=True)
    diagnosis = fields.TextField(null=True)
    drugs: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]

    raw_text = fields.TextField(null=True)
    ocr_raw: dict = fields.JSONField(null=True)  # type: ignore[assignment]

    file_path = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "scans"
        indexes = (("user_id", "id"), ("user_id", "created_at"))
