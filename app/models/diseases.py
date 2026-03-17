"""
질병 관련 모델 (ERD 기반)

📚 학습 포인트:
- FK가 없는 독립 테이블: 다른 테이블을 참조하지 않음
- kcd_code: 한국표준질병사인분류코드 (KCD)
"""

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation


class Disease(models.Model):
    """
    질병 마스터 테이블 (ERD: diseases).

    kcd_code는 한국표준질병사인분류코드 (KCD).
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    kcd_code = fields.CharField(max_length=20, null=True)
    description = fields.TextField(null=True)

    class Meta:
        table = "diseases"


class DiseaseGuideline(models.Model):
    """
    질병별 가이드라인 (ERD: disease_guidelines).

    질병에 대한 카테고리별 관리 지침 콘텐츠.
    """

    id = fields.IntField(pk=True)

    disease: ForeignKeyRelation["Disease"] = fields.ForeignKeyField(
        "models.Disease",
        on_delete=fields.CASCADE,
        related_name="guidelines",
    )
    category = fields.CharField(max_length=100)
    content = fields.TextField()
    source = fields.CharField(max_length=100, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "disease_guidelines"


class DiseaseCodeMapping(models.Model):
    """
    상세 KCD 코드 → 추천 anchor 코드 매핑 테이블.

    예: E1180(합병증을 동반하지 않은 2형 당뇨병) → E14(당뇨병)
    """

    id = fields.IntField(pk=True)
    code = fields.CharField(max_length=20, unique=True)  # 상세 KCD 코드
    name = fields.CharField(max_length=255)  # 상세 코드 한글명
    mapped_code = fields.CharField(max_length=20, index=True)  # anchor 코드
    mapped_name = fields.CharField(max_length=255)  # anchor 코드 한글명
    is_anchor = fields.BooleanField(default=False)  # 자기 자신이 anchor인지

    class Meta:
        table = "disease_code_mappings"
