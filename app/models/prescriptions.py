from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

if TYPE_CHECKING:
    from app.models.users import User
    from app.models.diseases import Disease
    from app.models.drugs import Drug


class Prescription(models.Model):
    id = fields.IntField(pk=True)

    user: ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="prescriptions",
    )

    # ✅ null=True 이므로 Optional로 선언
    disease: ForeignKeyRelation["Disease"] | None = fields.ForeignKeyField(
        "models.Disease",
        on_delete=fields.SET_NULL,
        null=True,
        related_name="prescriptions",
    )

    # ✅ null=True 이므로 Optional로 선언
    drug: ForeignKeyRelation["Drug"] | None = fields.ForeignKeyField(
        "models.Drug",
        on_delete=fields.SET_NULL,
        null=True,
        related_name="prescriptions",
    )

    dose_count = fields.IntField(null=True)
    dose_amount = fields.CharField(max_length=50, null=True)
    dose_unit = fields.CharField(max_length=20, null=True)
    start_date = fields.DateField(null=True)
    end_date = fields.DateField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "prescriptions"


class PrescriptionMemo(models.Model):
    id = fields.IntField(pk=True)

    prescription: ForeignKeyRelation["Prescription"] = fields.ForeignKeyField(
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

    prescription: ForeignKeyRelation["Prescription"] = fields.ForeignKeyField(
        "models.Prescription",
        on_delete=fields.CASCADE,
        related_name="intake_logs",
    )

    intake_date = fields.DateField(index=True)
    slot_label = fields.CharField(max_length=30, null=True)
    intake_datetime = fields.DatetimeField(null=True)

    status = fields.CharField(max_length=50)  # taken / skipped / delayed

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medication_intake_logs"
        indexes = (("intake_date", "status"),)