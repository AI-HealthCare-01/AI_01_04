from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from starlette import status

from app.dtos.medication import MedicationLogUpdateRequest
from app.utils.datetime import date_range_inclusive, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.progress import rate_bucket

# DB 붙이면 _MEM/_LOG_INDEX/_seed_if_empty 부분을 repo 조회/생성으로 교체하면 됨
# ===== 임시 In-Memory 저장소 (DB 붙으면 Repo로 교체) =====
# user_id -> date -> checklist items
# item: {"id": int, "label": str, "status": "taken|skipped|delayed", "intake_datetime": str|None}
_MEM: dict[int, dict[str, list[dict]]] = {}
# log_id -> (user_id, date)
_LOG_INDEX: dict[int, tuple[int, str]] = {}
_NEXT_LOG_ID = 1


def _seed_if_empty(user_id: int, date_str: str) -> None:
    """
    해당 날짜에 데이터 없으면 기본 체크리스트(아침/점심/저녁/자기전) 생성
    """
    global _NEXT_LOG_ID

    user_map = _MEM.setdefault(user_id, {})
    if date_str in user_map:
        return

    labels = ["아침", "점심", "저녁", "자기전"]
    items = []
    for lb in labels:
        log_id = _NEXT_LOG_ID
        _NEXT_LOG_ID += 1
        item = {"id": log_id, "label": lb, "status": "skipped", "intake_datetime": None}
        items.append(item)
        _LOG_INDEX[log_id] = (user_id, date_str)

    user_map[date_str] = items


def _calc_rate(items: list[dict]) -> int:
    if not items:
        return 0
    taken = sum(1 for x in items if x["status"] == "taken")
    total = len(items)
    return int(round((taken / total) * 100))


class MedicationService:
    async def list_history(self, user_id: int, date_from: str | None, date_to: str | None) -> dict:
        start, end = normalize_from_to(date_from, date_to)
        days = list(reversed(date_range_inclusive(start, end)))

        items = []
        for d in days:
            ds = d.isoformat()
            _seed_if_empty(user_id, ds)
            day_items = _MEM[user_id][ds]
            rate = _calc_rate(day_items)
            items.append({"date": ds, "rate": rate})

        return {"items": items}

    async def get_day_detail(self, user_id: int, date: str) -> dict:
        _seed_if_empty(user_id, date)
        items = _MEM[user_id][date]
        rate = _calc_rate(items)
        bucket = "none" if not items else rate_bucket(rate)

        return {
            "date": date,
            "rate": rate,
            "bucket": bucket,
            "items": items,
        }

    async def update_log(self, user_id: int, log_id: int, data: MedicationLogUpdateRequest) -> dict:
        key = _LOG_INDEX.get(log_id)
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="log not found.")

        owner_id, date_str = key
        if owner_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden.")

        # 해당 item 찾아서 업데이트
        items = _MEM[user_id][date_str]
        found = False
        for it in items:
            if it["id"] == log_id:
                it["status"] = data.status
                # taken이면 복용시간 기록, 아니면 제거(정책은 취향)
                it["intake_datetime"] = datetime.now().isoformat() if data.status == "taken" else None
                found = True
                break

        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="log not found in day.")

        # 업데이트 후 day 재계산해서 반환
        day = await self.get_day_detail(user_id=user_id, date=date_str)

        return {
            "log_id": log_id,
            "updated": True,
            "day": day,
        }

    async def ensure_day_seed(self, user_id: int, date: str) -> None:
        _seed_if_empty(user_id, date)

    async def ensure_range_seed(self, user_id: int, date_from: str, date_to: str) -> None:
        start = parse_date_yyyy_mm_dd(date_from)
        end = parse_date_yyyy_mm_dd(date_to)
        for d in date_range_inclusive(start, end):
            _seed_if_empty(user_id, d.isoformat())
