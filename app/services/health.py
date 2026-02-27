from __future__ import annotations

from fastapi import HTTPException
from starlette import status

from app.dtos.health import HealthLogUpdateRequest
from app.utils.datetime import date_range_inclusive, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.progress import rate_bucket

_MEM: dict[int, dict[str, list[dict]]] = {}
_LOG_INDEX: dict[int, tuple[int, str]] = {}
_NEXT_LOG_ID = 100000  # medication이랑 구분하려고 큰 숫자부터


def _seed_if_empty(user_id: int, date_str: str) -> None:
    global _NEXT_LOG_ID

    user_map = _MEM.setdefault(user_id, {})
    if date_str in user_map:
        return

    # 건강관리 체크리스트는 프로젝트 기획에 맞춰 항목 바꾸면 됨
    labels = ["물 마시기", "걷기", "스트레칭"]  # 예시
    items = []
    for lb in labels:
        log_id = _NEXT_LOG_ID
        _NEXT_LOG_ID += 1
        item = {"id": log_id, "label": lb, "status": "skipped"}
        items.append(item)
        _LOG_INDEX[log_id] = (user_id, date_str)

    user_map[date_str] = items


def _calc_rate(items: list[dict]) -> int:
    if not items:
        return 0
    done = sum(1 for x in items if x["status"] == "done")
    total = len(items)
    return int(round((done / total) * 100))


class HealthService:
    async def list_history(self, user_id: int, date_from: str | None, date_to: str | None) -> dict:
        start, end = normalize_from_to(date_from, date_to)
        days = list(reversed(date_range_inclusive(start, end)))

        rows = []
        for d in days:
            ds = d.isoformat()
            _seed_if_empty(user_id, ds)
            rate = _calc_rate(_MEM[user_id][ds])
            rows.append({"date": ds, "rate": rate})

        return {"items": rows}

    async def get_day_detail(self, user_id: int, date: str) -> dict:
        _seed_if_empty(user_id, date)
        items = _MEM[user_id][date]
        rate = _calc_rate(items)
        bucket = "none" if not items else rate_bucket(rate)

        return {"date": date, "rate": rate, "bucket": bucket, "items": items}

    async def update_log(self, user_id: int, log_id: int, data: HealthLogUpdateRequest) -> dict:
        key = _LOG_INDEX.get(log_id)
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="log not found.")

        owner_id, date_str = key
        if owner_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden.")

        items = _MEM[user_id][date_str]
        for it in items:
            if it["id"] == log_id:
                it["status"] = data.status
                break
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="log not found in day.")

        day = await self.get_day_detail(user_id=user_id, date=date_str)
        return {"log_id": log_id, "updated": True, "day": day}

    async def ensure_day_seed(self, user_id: int, date: str) -> None:
        _seed_if_empty(user_id, date)

    async def ensure_range_seed(self, user_id: int, date_from: str, date_to: str) -> None:
        start = parse_date_yyyy_mm_dd(date_from)
        end = parse_date_yyyy_mm_dd(date_to)
        for d in date_range_inclusive(start, end):
            _seed_if_empty(user_id, d.isoformat())
