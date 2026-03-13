"""건강관리 체크리스트 도메인 Repository.

HealthChecklistTemplate 및 HealthChecklistLog 조회/생성을 담당한다.
항상 user_id 스코프로 본인 데이터만 접근 가능하도록 보장한다.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.models.health import HealthChecklistLog, HealthChecklistTemplate


class HealthRepository:
    def __init__(self):
        self._tpl_model = HealthChecklistTemplate
        self._log_model = HealthChecklistLog

    async def list_active_templates(self) -> list[HealthChecklistTemplate]:
        """활성화된 체크리스트 템플릿 목록을 조회한다 (sort_order 오름차순).

        Returns:
            list[HealthChecklistTemplate]: is_active=True인 HealthChecklistTemplate 목록.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._tpl_model.filter(is_active=True).order_by("sort_order", "id").all()

    async def list_logs_by_user_date(self, user_id: int, dt: date) -> list[HealthChecklistLog]:
        """특정 날짜의 사용자 건강관리 로그 목록을 조회한다.

        Args:
            user_id (int): 조회할 사용자 ID.
            dt (date): 조회할 날짜.

        Returns:
            list[HealthChecklistLog]: template이 prefetch된 HealthChecklistLog 목록 (id 오름차순).

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._log_model.filter(user_id=user_id, date=dt).prefetch_related("template").order_by("id").all()

    async def get_by_id_for_user(self, user_id: int, log_id: int) -> HealthChecklistLog | None:
        """user_id 소유의 건강관리 로그를 단건 조회한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            log_id (int): 조회할 로그 ID.

        Returns:
            HealthChecklistLog | None: template이 prefetch된 HealthChecklistLog 객체. 없으면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        return await self._log_model.get_or_none(id=log_id, user_id=user_id).prefetch_related("template")

    async def get_or_create_log(
        self,
        user_id: int,
        template_id: int,
        dt: date,
        *,
        defaults: dict[str, Any],
    ) -> HealthChecklistLog:
        """날짜+템플릿 기준으로 로그를 조회하고 없으면 생성한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            template_id (int): 체크리스트 템플릿 ID.
            dt (date): 로그 날짜.
            defaults (dict[str, Any]): 생성 시 사용할 기본값 딕셔너리.

        Returns:
            HealthChecklistLog: 조회 또는 생성된 HealthChecklistLog 객체.

        Raises:
            OperationalError: DB 연결 오류 시.
        """
        obj = await self._log_model.get_or_none(user_id=user_id, template_id=template_id, date=dt)
        if obj:
            return obj
        return await self._log_model.create(user_id=user_id, template_id=template_id, date=dt, **defaults)
