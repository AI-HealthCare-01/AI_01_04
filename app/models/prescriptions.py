"""
처방전/복약 기록 모델 (ERD: prescriptions, medication_intake_logs)

- Prescription: 사용자 처방전 (drug, disease FK)
- PrescriptionMemo: 복약 메모 (효과/부작용)
- MedicationIntakeLog: 일자별 복약 슬롯 로그 (taken/skipped/delayed)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

if TYPE_CHECKING:
    from app.models.diseases import Disease
    from app.models.drugs import Drug
    from app.models.users import User


class Prescription(models.Model):
    """
    처방전 모델 (ERD: prescriptions).

    사용자 처방전 정보를 저장하며 drug, disease와 FK 관계.
    """

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
    dose_unit = fields.CharField(max_length=20, null=True)  # 단위 (정, ml, 캡슐, unit 등)
    dose_timing = fields.CharField(max_length=50, null=True)  # 복용시점 (식전, 식후, 자기전, 아침 저녁 등)
    start_date = fields.DateField(null=True)
    end_date = fields.DateField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "prescriptions"


class PrescriptionMemo(models.Model):
    """
    복약 메모 (ERD: prescription_memos).

    약 효과 및 부작용 기록.
    """

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
    복용 기록 (ERD: medication_intake_logs).

    일자별 복약 체크리스트 슬롯을 관리한다.

    Attributes:
        intake_date: 일자별 집계 기준.
        slot_label: 체크리스트 슬롯 (아침/점심/저녁/자기전).
        intake_datetime: taken이면 실제 복용 시각, 해제면 None.
        status: taken | skipped | delayed.
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
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medication_intake_logs"
        indexes = (("intake_date", "status"),)
