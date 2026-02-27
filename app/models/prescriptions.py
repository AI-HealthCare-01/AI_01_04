"""
처방전 관련 모델 (ERD 기반)

📚 학습 포인트:
- 여러 FK를 가진 테이블: users, diseases, drugs를 모두 참조
- CASCADE: 부모 삭제 시 자식도 삭제 (예: 사용자 삭제 → 처방전 삭제)
"""
from tortoise import fields, models


class Prescription(models.Model):
    """
    처방전 테이블 (ERD: prescriptions)

    - user: 누구의 처방인지
    - disease: 어떤 질병에 대한 처방인지
    - drug: 어떤 약인지
    - dose_*: 복용량 정보
    """

    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="prescriptions",
    )
    disease = fields.ForeignKeyField(
        "models.Disease",
        on_delete=fields.SET_NULL,
        null=True,
        related_name="prescriptions",
    )
    drug = fields.ForeignKeyField(
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
    """
    처방전 메모 (ERD: prescription_memos)

    사용자가 복용 후 효과/부작용을 기록
    """

    id = fields.IntField(pk=True)
    prescription = fields.ForeignKeyField(
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

    실제로 약을 먹은 시각과 상태 기록
    """

    id = fields.IntField(pk=True)
    prescription = fields.ForeignKeyField(
        "models.Prescription",
        on_delete=fields.CASCADE,
        related_name="intake_logs",
    )
    intake_datetime = fields.DatetimeField()
    status = fields.CharField(max_length=50)  # taken, skipped, missed 등
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "medication_intake_logs"
