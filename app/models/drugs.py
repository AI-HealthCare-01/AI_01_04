"""
약품 마스터 모델 (ERD 기반)

📚 학습 포인트:
- 마스터 데이터: prescriptions 등에서 FK로 참조됨
"""

from tortoise import fields, models


class Drug(models.Model):
    """
    약품 마스터 테이블 (ERD: drugs)
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    manufacturer = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "drugs"
