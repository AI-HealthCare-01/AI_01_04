"""
처방전 관련 모델 (ERD 기반)

📚 학습 포인트:
- 여러 FK를 가진 테이블: users, diseases, drugs를 모두 참조
- CASCADE: 부모 삭제 시 자식도 삭제 (예: 사용자 삭제 → 처방전 삭제)
"""

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

if TYPE_CHECKING:
    from app.models.diseases import Disease
    from app.models.drugs import Drug
    from app.models.users import User


class Prescription(models.Model):
    """
    처방전 테이블 (ERD: prescriptions)

    - user: 누구의 처방인지
    - disease: 어떤 질병에 대한 처방인지
    - drug: 어떤 약인지
    - dose_*: 복용량 정보
    """

    id = fields.IntField(pk=True)

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="prescriptions",
    )

    # ✅ null=True 이므로 Optional로 선언
    disease: ForeignKeyRelation[Disease] | None = fields.ForeignKeyField(
        "models.Disease",
        on_delete=fields.SET_NULL,
        null=True,
        related_name="prescriptions",
    )

    # ✅ null=True 이므로 Optional로 선언
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
    """
    처방전 메모 (ERD: prescription_memos)

    사용자가 복용 후 효과/부작용을 기록
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
    복용 기록 (ERD: medication_intake_logs)

    실제로 약을 먹은 시각과 상태 기록 + (EPIC4) 슬롯/일자 기반 체크리스트 지원
    """

    id = fields.IntField(pk=True)

    prescription: ForeignKeyRelation[Prescription] = fields.ForeignKeyField(
        "models.Prescription",
        on_delete=fields.CASCADE,
        related_name="intake_logs",
    )

    # ✅ EPIC4용: 일자별 조회/집계 빠르게
    intake_date = fields.DateField(index=True)

    # ✅ EPIC4용: 프론트 체크리스트 드롭다운/표시에 필요
    # 예: "아침", "점심", "저녁", "자기전"
    slot_label = fields.CharField(max_length=30, null=True)

    # 실제 복용 시각 (taken이면 now 세팅, 체크 해제면 null)
    intake_datetime = fields.DatetimeField(null=True)

    status = fields.CharField(max_length=50)  # taken, skipped, delayed 등

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medication_intake_logs"
        indexes = (("intake_date", "status"),)
