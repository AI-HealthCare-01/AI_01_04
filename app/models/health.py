"""
건강관리 체크리스트 모델 (ERD: health_checklist_templates, health_checklist_logs)

- HealthChecklistTemplate: 체크리스트 항목 마스터 (물 마시기, 걸기 등)
- HealthChecklistLog: 사용자 일자별 체크 로그 (done/skipped)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

if TYPE_CHECKING:
    from app.models.users import User

HealthStatus = Literal["done", "skipped"]


class HealthChecklistTemplate(models.Model):
    """
    건강관리 체크리스트 템플릿(마스터)

    예: 물 마시기, 걷기, 스트레칭 ...
    """

    id = fields.IntField(pk=True)
    label = fields.CharField(max_length=100)
    is_active = fields.BooleanField(default=True)
    sort_order = fields.IntField(default=0)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "health_checklist_templates"
        ordering = ["sort_order", "id"]


class HealthChecklistLog(models.Model):
    """
    사용자 일자별 건강관리 로그

    - date 기준으로 하루 체크리스트 조회/집계
    - status: done / skipped
    - checked_at: done이면 now, 해제면 None
    """

    id = fields.IntField(pk=True)

    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="health_checklist_logs",
    )

    template: ForeignKeyRelation[HealthChecklistTemplate] = fields.ForeignKeyField(
        "models.HealthChecklistTemplate",
        on_delete=fields.CASCADE,
        related_name="logs",
    )

    date = fields.DateField(index=True)
    status = fields.CharField(max_length=20)  # done | skipped
    checked_at = fields.DatetimeField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "health_checklist_logs"
        indexes = (("user_id", "date"), ("date", "status"))
