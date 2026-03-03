from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

if TYPE_CHECKING:
    from app.models.diseases import Disease
    from app.models.drugs import Drug
    from app.models.users import User


class Prescription(models.Model):
    id = fields.IntField(pk=True)

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="prescriptions",
    )

    disease: ForeignKeyRelation[Disease] | None = fields.ForeignKeyField(
        "models.Disease",
        on_delete=fields.SET_NULL,
        null=True,
        related_name="prescriptions",
    )

    drug: ForeignKeyRelation[Drug] | None = fields.ForeignKeyField(
        "models.Drug",
        on_delete=fields.SET_NULL,
        null=True,
        related_name="prescriptions",
    )

    dose_count = fields.IntField(null=True)  # 1일 복용 횟수
    dose_amount = fields.CharField(max_length=50, null=True)  # 1회 복용량 (예: "1정")
    dose_unit = fields.CharField(max_length=20, null=True)  # 단위 (정, ml 등)
    start_date = fields.DateField(null=True)
    end_date = fields.DateField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "prescriptions"


class PrescriptionMemo(models.Model):
    id = fields.IntField(pk=True)

    prescription: ForeignKeyRelation[Prescription] = fields.ForeignKeyField(
        "models.Prescription",
        on_delete=fields.CASCADE,
        related_name="memos",
    )

    memo_datetime = fields.DatetimeField()
    effect = fields.TextField(null=True)
    side_effect = fields.TextField(null=True)

    class Meta:
        table = "prescription_memos"


class MedicationIntakeLog(models.Model):
    """
    복용 기록 (ERD: medication_intake_logs)

    EPIC4(일자별 이력/체크리스트/달성률) 지원:
    - intake_date: 일자별 집계
    - slot_label: 체크리스트 슬롯(아침/점심/저녁/자기전)
    - intake_datetime: taken이면 now, 해제면 None
    """

    id = fields.IntField(pk=True)

    prescription: ForeignKeyRelation[Prescription] = fields.ForeignKeyField(
        "models.Prescription",
        on_delete=fields.CASCADE,
        related_name="intake_logs",
    )

    # ✅ EPIC4
    intake_date = fields.DateField(index=True)
    slot_label = fields.CharField(max_length=30, null=True)
    intake_datetime = fields.DatetimeField(null=True)

    status = fields.CharField(max_length=50)  # taken, skipped, delayed 등
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "medication_intake_logs"
        # (선택) 조회 최적화
        indexes = (
            ("intake_date", "status"),
            ("prescription_id", "intake_date"),
        )
