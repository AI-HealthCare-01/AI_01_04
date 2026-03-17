"""
약품 마스터 모델 (ERD 기반)

📚 학습 포인트:
- 마스터 데이터: prescriptions 등에서 FK로 참조됨
"""

from tortoise import fields, models


class Drug(models.Model):
    """
    약품 마스터 테이블 (ERD: drugs).

    prescriptions 등에서 FK로 참조되는 마스터 데이터.
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=500)
    manufacturer = fields.CharField(max_length=255, null=True)
    raw_material = fields.TextField(null=True)       # 원료성분
    raw_material_en = fields.TextField(null=True)    # 영문성분명
    efficacy = fields.TextField(null=True)           # 효능효과
    dosage = fields.TextField(null=True)             # 용법용량
    caution_1 = fields.TextField(null=True)          # 사용상의주의사항1
    caution_2 = fields.TextField(null=True)          # 사용상의주의사항2
    caution_3 = fields.TextField(null=True)          # 사용상의주의사항3
    caution_4 = fields.TextField(null=True)          # 사용상의주의사항4
    storage = fields.TextField(null=True)            # 저장방법
    change_log = fields.TextField(null=True)         # 변경내용 (없으면 null)
    main_ingredient = fields.TextField(null=True)    # 주성분명

    class Meta:
        table = "drugs"
