from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import HTTPException
from starlette import status

from app.dtos.medication import MedicationLogUpdateRequest
from app.models.prescriptions import MedicationIntakeLog
from app.utils.datetime import DateTimeError, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.pagination import paginate_list
from app.utils.progress import rate_bucket

SortOrder = Literal["asc", "desc"]


def _calc_rate_from_logs(logs: list[MedicationIntakeLog]) -> int:
    if not logs:
        return 0
    taken = sum(1 for x in logs if x.status == "taken")
    total = len(logs)
    return int(round((taken / total) * 100))


def _make_label(log: MedicationIntakeLog) -> str:
    # 우선순위: slot_label > drug name > fallback
    if getattr(log, "slot_label", None):
        return log.slot_label  # type: ignore[return-value]
    # select_related("prescription__drug")가 되어있다는 전제
    drug = getattr(getattr(log, "prescription", None), "drug", None)
    if drug and getattr(drug, "name", None):
        return str(drug.name)
    return "복용"


class MedicationService:
    async def list_history(
        self,
        user_id: int,
        date_from: str | None,
        date_to: str | None,
        page: int = 1,
        size: int = 14,
        sort: SortOrder = "desc",
    ) -> dict:
        try:
            start, end = normalize_from_to(date_from, date_to)
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        # 기간 내 로그를 전부 가져와 날짜별로 묶기
        # (Prescription -> User 조인)
        logs = await MedicationIntakeLog.filter(
            prescription__user_id=user_id,
            intake_date__gte=start,
            intake_date__lte=end,
        ).all()

        by_date: dict[str, list[MedicationIntakeLog]] = {}
        for lg in logs:
            ds = lg.intake_date.isoformat()
            by_date.setdefault(ds, []).append(lg)

        # 요청 구간의 "모든 날짜"를 row로 반환 (로그 없어도 row는 존재)
        days = []
        cur = start
        while cur <= end:
            days.append(cur)
            cur = cur.fromordinal(cur.toordinal() + 1)

        if sort == "desc":
            days = list(reversed(days))

        rows: list[dict] = []
        for d in days:
            ds = d.isoformat()
            day_logs = by_date.get(ds, [])
            rate = _calc_rate_from_logs(day_logs)
            bucket = "none" if not day_logs else rate_bucket(rate)

            rows.append(
                {
                    "date": ds,
                    "rate": rate,
                    "bucket": bucket,
                    "detail_key": ds,
                }
            )

        return paginate_list(rows, page=page, page_size=size)

    async def get_day_detail(self, user_id: int, date: str) -> dict:
        # 날짜 형식 검증
        try:
            dt = parse_date_yyyy_mm_dd(date)
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        logs = await MedicationIntakeLog.filter(
            prescription__user_id=user_id,
            intake_date=dt,
        ).select_related("prescription", "prescription__drug").all()

        # 프론트 체크리스트에 필요한 필드 구성
        items = []
        for lg in logs:
            items.append(
                {
                    "id": lg.id,
                    "label": _make_label(lg),
                    "status": lg.status,
                    "intake_datetime": lg.intake_datetime.isoformat() if lg.intake_datetime else None,
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

    async def update_log(self, user_id: int, log_id: int, data: MedicationLogUpdateRequest) -> dict:
        log = await MedicationIntakeLog.filter(id=log_id).select_related("prescription").first()
        if not log:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="log not found.")
        if log.prescription.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden.")

        # 상태 변경 + 즉시 반영 규칙
        log.status = data.status
        if data.status == "taken":
            log.intake_datetime = datetime.now()
        else:
            # 체크 해제/지연이면 복용 시각 제거(정책)
            log.intake_datetime = None

        await log.save()

        # 저장 직후 day 재계산해서 반환 (DoD: 즉시 일치)
        day = await self.get_day_detail(user_id=user_id, date=log.intake_date.isoformat())

        return {
            "log_id": log_id,
            "updated": True,
            "day": day,
        }