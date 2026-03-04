from __future__ import annotations

from datetime import date
from typing import Any

from app.models.health import HealthChecklistLog, HealthChecklistTemplate


class HealthRepository:
    def __init__(self):
        self._tpl_model = HealthChecklistTemplate
        self._log_model = HealthChecklistLog

    async def list_active_templates(self) -> list[HealthChecklistTemplate]:
        return await self._tpl_model.filter(is_active=True).order_by("sort_order", "id").all()

    async def list_logs_by_user_date(self, user_id: int, dt: date) -> list[HealthChecklistLog]:
        return await self._log_model.filter(user_id=user_id, date=dt).prefetch_related("template").order_by("id").all()

    async def get_by_id_for_user(self, user_id: int, log_id: int) -> HealthChecklistLog | None:
        return await self._log_model.get_or_none(id=log_id, user_id=user_id).prefetch_related("template")

    async def get_or_create_log(
        self,
        user_id: int,
        template_id: int,
        dt: date,
        *,
        defaults: dict[str, Any],
    ) -> HealthChecklistLog:
        obj = await self._log_model.get_or_none(user_id=user_id, template_id=template_id, date=dt)
        if obj:
            return obj
        return await self._log_model.create(user_id=user_id, template_id=template_id, date=dt, **defaults)
