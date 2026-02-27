"""
질병 관련 모델 (ERD 기반)

📚 학습 포인트:
- FK가 없는 독립 테이블: 다른 테이블을 참조하지 않음
- icd_code: 국제질병분류코드 (WHO 표준)
"""

from tortoise import fields, models


class Disease(models.Model):
    """
    질병 마스터 테이블 (ERD: diseases)
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    icd_code = fields.CharField(max_length=20, null=True)
    description = fields.TextField(null=True)

    class Meta:
        table = "diseases"


class DiseaseGuideline(models.Model):
    """
    질병별 가이드라인 (ERD: disease_guidelines)

    diseases 테이블과 N:1 관계
    - 한 질병에 여러 가이드라인 (category별: 증상, 치료법, 주의사항 등)
    """

    id = fields.IntField(pk=True)
    disease = fields.ForeignKeyField(
        "models.Disease",
        on_delete=fields.CASCADE,
        related_name="guidelines",
    )
    category = fields.CharField(max_length=100)
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "disease_guidelines"
