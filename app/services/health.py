"""
건강관리 체크리스트 서비스

- 일자별 체크리스트 시드(seed) 및 조회
- 달성률 계산 및 로그 업데이트 담당
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from fastapi import HTTPException
from starlette import status

from app.dtos.health import HealthLogUpdateRequest
from app.models.health import HealthChecklistLog
from app.repositories.health_repository import HealthRepository
from app.utils.datetime import DateTimeError, date_range_inclusive, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.progress import rate_bucket


def _calc_rate_from_logs(logs: list[HealthChecklistLog]) -> int:
    """체크리스트 로그에서 done 비율(%) 계산"""
    if not logs:
        return 0
    done = sum(1 for lg in logs if lg.status == "done")
    return int(round((done / len(logs)) * 100))


class HealthService:
    def __init__(self):
        self.health_repo = HealthRepository()

    async def ensure_day_seed(self, *, user_id: int, date: str) -> None:
        """외부 서비스에서 호출하는 시드 진입점"""
        await self._seed_day_if_empty(user_id=user_id, date_str=date)

    async def _seed_day_if_empty(self, *, user_id: int, date_str: str) -> None:
        """
        해당 날짜에 로그가 없으면 활성 템플릿 기준으로 skipped 상태로 생성

        - 이미 로그가 있으면 아무것도 하지 않음 (멱등성 보장)
        """
        d = parse_date_yyyy_mm_dd(date_str)

        existing_cnt = await HealthChecklistLog.filter(user_id=user_id, date=d).count()
        if existing_cnt > 0:
            return

        templates = await self.health_repo.list_active_templates()
        if not templates:
            return

        logs_to_create: list[HealthChecklistLog] = []
        for t in templates:
            logs_to_create.append(
                HealthChecklistLog(
                    user_id=user_id,
                    template_id=t.id,
                    date=d,
                    status="skipped",
                    checked_at=None,
                )
            )

        await HealthChecklistLog.bulk_create(logs_to_create)

    async def list_history(self, user_id: int, date_from: str | None, date_to: str | None) -> dict:
        """기간별 건강관리 이력 조회 (날짜 내림차순)"""
        try:
            start, end = normalize_from_to(date_from, date_to)
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        days = list(reversed(list(date_range_inclusive(start, end))))

        rows: list[dict] = []
        for d in days:
            ds = d.isoformat()
            await self._seed_day_if_empty(user_id=user_id, date_str=ds)

            day_logs = await HealthChecklistLog.filter(user_id=user_id, date=d).all()
            rate = _calc_rate_from_logs(day_logs)

            rows.append(
                {
                    "date": ds,
                    "rate": rate,
                }
            )

        return {"items": rows}

    async def get_day_detail(self, user_id: int, date: str) -> dict:
        """특정 날짜의 체크리스트 상세 조회 (없으면 시드 후 반환)"""
        try:
            d = parse_date_yyyy_mm_dd(date)
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        await self._seed_day_if_empty(user_id=user_id, date_str=date)

        logs = await self.health_repo.list_logs_by_user_date(user_id=user_id, dt=d)

        items: list[dict] = []
        for lg in logs:
            items.append(
                {
                    "id": lg.id,
                    "label": lg.template.label if lg.template else "",
                    "status": lg.status,
                }
            )

        rate = _calc_rate_from_logs(logs)
        bucket = "none" if not logs else rate_bucket(rate)

        return {
            "date": date,
            "rate": rate,
            "bucket": bucket,
            "items": items,
        }

    async def update_log(self, user_id: int, log_id: int, data: HealthLogUpdateRequest) -> dict:
        """건강관리 로그 상태 업데이트 (done/skipped)"""
        log = await self.health_repo.get_by_id_for_user(user_id=user_id, log_id=log_id)
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="log not found.")

        log.status = data.status

        log_any = cast(Any, log)
        if data.status == "done":
            log_any.checked_at = datetime.now()
        else:
            log_any.checked_at = None

        await log.save()

        day = await self.get_day_detail(user_id=user_id, date=log.date.isoformat())
        return {"log_id": log_id, "updated": True, "day": day}
