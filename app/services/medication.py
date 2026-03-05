from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Literal, cast

from fastapi import HTTPException
from starlette import status
from tortoise.expressions import Q

from app.dtos.medication import MedicationLogUpdateRequest
from app.models.prescriptions import MedicationIntakeLog, Prescription
from app.repositories.medication_intake_repository import MedicationIntakeRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.utils.datetime import DateTimeError, date_range_inclusive, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.pagination import build_page_meta
from app.utils.progress import rate_bucket

logger = logging.getLogger(__name__)

SortOrder = Literal["asc", "desc"]


def _calc_rate_from_logs(logs: list[MedicationIntakeLog]) -> int:
    if not logs:
        return 0
    taken = sum(1 for lg in logs if lg.status == "taken")
    return int(round((taken / len(logs)) * 100))


def _slots_by_dose_count(dose_count: int | None) -> list[str]:
    if dose_count is None:
        return ["아침"]
    if dose_count >= 4:
        return ["아침", "점심", "저녁", "자기전"]
    if dose_count == 3:
        return ["아침", "점심", "저녁"]
    if dose_count == 2:
        return ["아침", "저녁"]
    return ["아침"]


def _make_label(log: MedicationIntakeLog) -> str:
    slot = getattr(log, "slot_label", None)
    if slot:
        return str(slot)

    drug = getattr(getattr(log, "prescription", None), "drug", None)
    if drug and getattr(drug, "name", None):
        return str(drug.name)

    return "복용"


class MedicationService:
    def __init__(self):
        self.prescription_repo = PrescriptionRepository()
        self.medication_repo = MedicationIntakeRepository()

    async def _seed_day_if_empty(self, *, user_id: int, date_str: str) -> None:
        d = parse_date_yyyy_mm_dd(date_str)

        existing_cnt = await MedicationIntakeLog.filter(
            prescription__user_id=user_id,
            intake_date=d,
        ).count()
        if existing_cnt > 0:
            return

        pres_q = Q(user_id=user_id)
        pres_q &= Q(start_date__lte=d) | Q(start_date__isnull=True)
        pres_q &= Q(end_date__gte=d) | Q(end_date__isnull=True)

        prescriptions = await Prescription.filter(pres_q).all()
        if not prescriptions:
            return

        logs_to_create: list[MedicationIntakeLog] = []
        for p in prescriptions:
            for sl in _slots_by_dose_count(p.dose_count):
                logs_to_create.append(
                    MedicationIntakeLog(
                        prescription_id=p.id,
                        intake_date=d,
                        slot_label=sl,
                        status="skipped",
                        intake_datetime=None,
                    )
                )

        await MedicationIntakeLog.bulk_create(logs_to_create)

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

        days = date_range_inclusive(start, end)
        if sort == "desc":
            days = list(reversed(days))

        total = len(days)
        offset = (page - 1) * size
        sliced = days[offset : offset + size]

        rows: list[dict] = []
        for d in sliced:
            ds = d.isoformat()
            await self._seed_day_if_empty(user_id=user_id, date_str=ds)

            day_logs = await MedicationIntakeLog.filter(
                prescription__user_id=user_id,
                intake_date=d,
            ).all()

            rate = _calc_rate_from_logs(day_logs)
            bucket = "none" if not day_logs else rate_bucket(rate)

            rows.append({"date": ds, "rate": rate, "bucket": bucket, "detail_key": ds})

        meta = build_page_meta(total=total, page=page, page_size=size)
        return {"items": rows, "meta": meta}

    async def get_day_detail(self, user_id: int, date: str) -> dict:
        try:
            dt = parse_date_yyyy_mm_dd(date)
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        await self._seed_day_if_empty(user_id=user_id, date_str=date)

        logs = (
            await MedicationIntakeLog.filter(
                prescription__user_id=user_id,
                intake_date=dt,
            )
            .select_related("prescription", "prescription__drug")
            .order_by("id")
            .all()
        )

        items: list[dict] = []
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

        return {"date": date, "rate": rate, "bucket": bucket, "items": items}

    async def update_log(self, user_id: int, log_id: int, data: MedicationLogUpdateRequest) -> dict:
        try:
            log = await self.medication_repo.get_by_id_for_user(user_id, log_id)
            if not log:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="log not found.")

            await log.fetch_related("prescription")

            log.status = data.status

            # mypy가 intake_datetime을 datetime(Non-Optional)로 추론하는 환경이라,
            # Any 캐스트로 속성 대입만 타입체크에서 제외
            log_any = cast(Any, log)
            if data.status == "taken":
                log_any.intake_datetime = datetime.now()
            else:
                log_any.intake_datetime = None

            await log.save()

            day = await self.get_day_detail(user_id=user_id, date=log.intake_date.isoformat())
            return {"log_id": log_id, "updated": True, "day": day}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("update_log failed")
            raise HTTPException(status_code=500, detail=str(e)) from e
