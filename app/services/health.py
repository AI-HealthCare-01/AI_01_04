from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from fastapi import HTTPException
from starlette import status

from app.dtos.health import HealthLogUpdateRequest
from app.models.health import HealthChecklistLog, HealthChecklistTemplate
from app.utils.datetime import DateTimeError, date_range_inclusive, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.progress import rate_bucket


def _calc_rate_from_logs(logs: list[HealthChecklistLog]) -> int:
    if not logs:
        return 0
    done = sum(1 for lg in logs if lg.status == "done")
    return int(round((done / len(logs)) * 100))


class HealthService:
    async def _seed_day_if_empty(self, *, user_id: int, date_str: str) -> None:
        d = parse_date_yyyy_mm_dd(date_str)

        existing_cnt = await HealthChecklistLog.filter(user_id=user_id, date=d).count()
        if existing_cnt > 0:
            return

        templates = await HealthChecklistTemplate.filter(is_active=True).order_by("sort_order", "id").all()
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
            rows.append({"date": ds, "rate": rate})

        return {"items": rows}

    async def get_day_detail(self, user_id: int, date: str) -> dict:
        try:
            d = parse_date_yyyy_mm_dd(date)
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        await self._seed_day_if_empty(user_id=user_id, date_str=date)

        logs = await HealthChecklistLog.filter(user_id=user_id, date=d).select_related("template").order_by("id").all()

        items: list[dict] = []
        for lg in logs:
            items.append(
                {
                    "id": lg.id,
                    "label": lg.template.label,
                    "status": lg.status,
                }
            )

        rate = _calc_rate_from_logs(logs)
        bucket = "none" if not logs else rate_bucket(rate)

        return {"date": date, "rate": rate, "bucket": bucket, "items": items}

    async def update_log(self, user_id: int, log_id: int, data: HealthLogUpdateRequest) -> dict:
        log = await HealthChecklistLog.filter(id=log_id, user_id=user_id).select_related("template").first()
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="log not found.")

        log.status = data.status

        # mypy/ruff 대응: Optional 속성 대입은 Any로 캐스팅
        log_any = cast(Any, log)
        if data.status == "done":
            log_any.checked_at = datetime.now()
        else:
            log_any.checked_at = None

        await log.save()

        day = await self.get_day_detail(user_id=user_id, date=log.date.isoformat())
        return {"log_id": log_id, "updated": True, "day": day}
