"""복약 관리 서비스.

일자별 복약 로그 시드(seed) 및 조회, 복약 슬롯 생성, 달성률 계산, 로그 상태 업데이트를 담당한다.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Literal, cast

from fastapi import HTTPException
from starlette import status
from tortoise.expressions import Q

from app.dtos.medication import MedicationLogUpdateRequest
from app.models.prescriptions import MedicationIntakeLog, Prescription
from app.repositories.medication_intake_repository import MedicationIntakeRepository
from app.repositories.prescription_repository import PrescriptionRepository
from app.utils.cache import cache_delete
from app.utils.datetime import DateTimeError, date_range_inclusive, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.pagination import build_page_meta
from app.utils.progress import rate_bucket

logger = logging.getLogger(__name__)

SortOrder = Literal["asc", "desc"]

# ✅ DTO에 맞춘 status 고정
AllowedStatus = Literal["taken", "skipped", "delayed"]


def _log_key(lg: MedicationIntakeLog) -> tuple[str, str]:
    """로그의 (drug_name, slot_label) 키를 반환한다."""
    drug = getattr(getattr(lg, "prescription", None), "drug", None)
    return (getattr(drug, "name", "") if drug else "", getattr(lg, "slot_label", "") or "")


def _dedup_logs(logs: list[MedicationIntakeLog]) -> list[MedicationIntakeLog]:
    """같은 약품+슬롯 조합의 중복 로그를 제거한다. taken 상태 우선."""
    best: dict[tuple[str, str], MedicationIntakeLog] = {}
    for lg in logs:
        key = _log_key(lg)
        prev = best.get(key)
        if prev is None or (prev.status != "taken" and lg.status == "taken"):
            best[key] = lg
    return list(best.values())


def _calc_rate_from_logs(logs: list[MedicationIntakeLog]) -> int:
    """복약 로그에서 taken 비율(%)을 계산한다.

    Args:
        logs (list[MedicationIntakeLog]): 계산할 로그 목록.

    Returns:
        int: taken 비율 (0~100).
    """
    if not logs:
        return 0
    taken = sum(1 for lg in logs if lg.status == "taken")
    return int(round((taken / len(logs)) * 100))


# dose_timing 문자열 → 슬롯 매핑
_TIMING_SLOT_MAP: dict[str, list[str]] = {
    # 시간대 직접 지정
    "아침": ["아침"],
    "점심": ["점심"],
    "저녁": ["저녁"],
    "자기 전": ["자기 전"],
    "자기전": ["자기 전"],
    # 시간대 + 식전/식후 (TIMING_OPTIONS 선택지)
    "아침 식후": ["아침"],
    "아침 식전": ["아침"],
    "점심 식후": ["점심"],
    "점심 식전": ["점심"],
    "저녁 식후": ["저녁"],
    "저녁 식전": ["저녁"],
    # 단순 식전/식후 — dose_count 기반 폴백
    "식전": ["아침"],
    "식후": ["아침"],
    "식후30분후": ["아침"],
    "필요시": ["아침"],
    # 복합 시간대
    "아침 점심": ["아침", "점심"],
    "아침 저녁": ["아침", "저녁"],
    "점심 저녁": ["점심", "저녁"],
    "아침 점심 저녁": ["아침", "점심", "저녁"],
    "아침 점심 저녁 자기 전": ["아침", "점심", "저녁", "자기 전"],
    "아침 점심 저녁 자기전": ["아침", "점심", "저녁", "자기 전"],
}

# dose_count 기반 폴백 대상 (len==1 이고 슬롯이 "아침"인 것들)
_FALLBACK_TO_DOSE_COUNT = {"식전", "식후", "식후30분후", "필요시"}


# 단일 시간대 지정 키 (슬롯 1개만 매핑되는 것들)
_SINGLE_SLOT_TIMINGS = {
    "아침", "점심", "저녁",
    "아침 식후", "아침 식전", "점심 식후", "점심 식전", "저녁 식후", "저녁 식전",
}


def _slots_for_prescription(p: Prescription) -> list[str]:
    """처방전의 dose_timing 또는 dose_count 기반으로 복약 슬롯을 반환한다."""
    timing = getattr(p, "dose_timing", None)
    if timing:
        timing = timing.strip()
        if timing in _TIMING_SLOT_MAP:
            # 단순 식전/식후 등은 dose_count로 확장
            if timing in _FALLBACK_TO_DOSE_COUNT and (p.dose_count or 1) > 1:
                return _slots_by_dose_count(p.dose_count)
            mapped = _TIMING_SLOT_MAP[timing]
            # 단일 시간대 지정인데 dose_count가 더 크면 dose_count 기반으로 확장
            if timing in _SINGLE_SLOT_TIMINGS and (p.dose_count or 1) > len(mapped):
                return _slots_by_dose_count(p.dose_count)
            return mapped
    return _slots_by_dose_count(p.dose_count)


def _slots_by_dose_count(dose_count: int | None) -> list[str]:
    """일일 복용 횟수에 따른 복약 슬롯 목록을 반환한다 (아침/점심/저녁/자기 전).

    Args:
        dose_count (int | None): 1일 복용 횟수. None이면 1회로 처리.

    Returns:
        list[str]: 복약 슬롯 레이블 목록.
    """
    if dose_count is None:
        return ["아침"]
    if dose_count >= 4:
        return ["아침", "점심", "저녁", "자기 전"]
    if dose_count == 3:
        return ["아침", "점심", "저녁"]
    if dose_count == 2:
        return ["아침", "저녁"]
    return ["아침"]


def _make_label(log: MedicationIntakeLog) -> str:
    """복약 로그의 표시 레이블을 반환한다 (슬롯명 > 약품명 > 기본값 순).

    Args:
        log (MedicationIntakeLog): 레이블을 추출할 복약 로그 객체.

    Returns:
        str: 표시할 레이블 문자열.
    """
    slot = getattr(log, "slot_label", None)
    if slot:
        return str(slot)

    drug = getattr(getattr(log, "prescription", None), "drug", None)
    if drug and getattr(drug, "name", None):
        return str(drug.name)

    return "복용"


def _normalize_status(raw: str) -> AllowedStatus:
    """
    DB에 과거 값(missed 등)이 섞여있어도 API 응답/업데이트는 DTO 스펙으로 고정.
    """
    if raw == "taken":
        return "taken"
    if raw == "delayed":
        return "delayed"
    # 그 외는 skipped로 정규화 (missed 포함)
    return "skipped"


class MedicationService:
    def __init__(self):
        self.prescription_repo = PrescriptionRepository()
        self.medication_repo = MedicationIntakeRepository()

    async def ensure_day_seed(self, *, user_id: int, date: str) -> None:
        """외부 서비스에서 호출하는 시드 진입점."""
        await self._seed_day_if_empty(user_id=user_id, date_str=date)

    @staticmethod
    async def _earliest_scan_date(user_id: int) -> date | None:
        """사용자의 가장 오래된 처방 start_date를 반환한다."""
        row = await Prescription.filter(
            user_id=user_id, start_date__isnull=False
        ).order_by("start_date").first()
        return row.start_date if row else None

    async def _extend_expired_prescriptions(self, user_id: int, today: Any) -> None:
        """복용 완료(taken) 기록이 전혀 없는 만료 처방전의 end_date를 오늘로 연장한다."""
        expired = await Prescription.filter(
            user_id=user_id,
            end_date__lt=today,
        ).all()
        for p in expired:
            has_taken = await MedicationIntakeLog.filter(
                prescription_id=p.id,
                status="taken",
            ).exists()
            if not has_taken:
                p.end_date = today
                await p.save(update_fields=["end_date"])

    async def _seed_day_if_empty(self, *, user_id: int, date_str: str) -> None:
        """해당 날짜에 복약 로그가 없으면 유효한 처방전 기준으로 skipped 상태로 생성한다.

        이미 로그가 있으면 아무것도 하지 않아 멱등성을 보장한다.
        유효한 처방전: start_date <= 날짜 <= end_date.
        만료된 처방전 중 taken 기록이 없으면 end_date를 오늘로 자동 연장한다.

        Args:
            user_id (int): 시드를 생성할 사용자 ID.
            date_str (str): 시드를 생성할 날짜 (YYYY-MM-DD).
        """
        d = parse_date_yyyy_mm_dd(date_str)

        await self._extend_expired_prescriptions(user_id, d)

        pres_q = Q(user_id=user_id)
        pres_q &= Q(start_date__lte=d) | Q(start_date__isnull=True)
        pres_q &= Q(end_date__gte=d) | Q(end_date__isnull=True)

        prescriptions = await Prescription.filter(pres_q).all()
        if not prescriptions:
            return

        existing_pres_ids = set(
            await MedicationIntakeLog.filter(
                prescription__user_id=user_id,
                intake_date=d,
            ).values_list("prescription_id", flat=True)
        )

        logs_to_create: list[MedicationIntakeLog] = []
        for p in prescriptions:
            if p.id in existing_pres_ids:
                continue
            for sl in _slots_for_prescription(p):
                logs_to_create.append(
                    MedicationIntakeLog(
                        prescription_id=p.id,
                        intake_date=d,
                        slot_label=sl,
                        status="skipped",  # ✅ seed는 기본 skipped
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
        """기간별 복약 이력을 조회한다 (날짜별 달성률 포함).

        Args:
            user_id (int): 조회할 사용자 ID.
            date_from (str | None): 조회 시작일 (YYYY-MM-DD). None이면 30일 전.
            date_to (str | None): 조회 종료일 (YYYY-MM-DD). None이면 오늘.
            page (int): 페이지 번호 (1-based). 기본값 1.
            size (int): 페이지당 항목 수. 기본값 14.
            sort (SortOrder): 정렬 방향 (asc/desc). 기본값 desc.

        Returns:
            dict: items와 meta가 담긴 딕셔너리.

        Raises:
            HTTPException: 날짜 형식 오류 또는 종료일이 시작일보다 앞설 시 400.
        """
        try:
            start, end = normalize_from_to(date_from, date_to)
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        # 사용자의 첫 스캔 날짜 이전은 표시하지 않음
        earliest = await self._earliest_scan_date(user_id)
        if earliest and start < earliest:
            start = earliest

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

            day_logs = (
                await MedicationIntakeLog.filter(
                    prescription__user_id=user_id,
                    intake_date=d,
                )
                .select_related("prescription", "prescription__drug")
                .all()
            )

            unique_logs = _dedup_logs(day_logs)
            rate = _calc_rate_from_logs(unique_logs)
            bucket = "none" if not unique_logs else rate_bucket(rate)

            rows.append({"date": ds, "rate": rate, "bucket": bucket, "detail_key": ds})

        meta = build_page_meta(total=total, page=page, page_size=size)
        return {"items": rows, "meta": meta}

    async def get_day_detail(self, user_id: int, date: str) -> dict:
        """특정 날짜의 복약 슬롯 상세를 조회한다 (없으면 시드 후 반환).

        Args:
            user_id (int): 조회할 사용자 ID.
            date (str): 조회할 날짜 (YYYY-MM-DD).

        Returns:
            dict: date, rate, bucket, items가 담긴 딕셔너리.

        Raises:
            HTTPException: 날짜 형식 오류 시 400.
        """
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
        deduped_logs = _dedup_logs(logs)
        for lg in deduped_logs:
            drug = getattr(getattr(lg, "prescription", None), "drug", None)
            presc = getattr(lg, "prescription", None)
            items.append(
                {
                    "id": lg.id,
                    "label": _make_label(lg),
                    "status": _normalize_status(lg.status),
                    "intake_datetime": lg.intake_datetime.isoformat() if lg.intake_datetime else None,
                    "drug_name": getattr(drug, "name", None) if drug else None,
                    "dose_amount": getattr(presc, "dose_amount", None) if presc else None,
                    "dose_unit": getattr(presc, "dose_unit", None) if presc else None,
                    "dose_timing": getattr(presc, "dose_timing", None) if presc else None,
                }
            )

        rate = _calc_rate_from_logs(deduped_logs)
        bucket = "none" if not logs else rate_bucket(rate)

        return {"date": date, "rate": rate, "bucket": bucket, "items": items}

    async def update_log(self, user_id: int, log_id: int, data: MedicationLogUpdateRequest) -> dict:
        """복약 로그 상태를 업데이트한다 (taken/skipped/delayed).

        Args:
            user_id (int): 소유자 사용자 ID.
            log_id (int): 업데이트할 로그 ID.
            data (MedicationLogUpdateRequest): 새 상태가 담긴 요청 데이터.

        Returns:
            dict: log_id, updated, day가 담긴 딕셔너리.

        Raises:
            HTTPException: 로그가 없거나 소유자가 다를 시 404, 예기치 않은 오류 시 500.
        """
        try:
            log = await self.medication_repo.get_by_id_for_user(user_id, log_id)
            if not log:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="log not found.")

            # ✅ DTO 기준으로만 저장
            new_status: AllowedStatus = _normalize_status(data.status)
            log.status = new_status

            log_any = cast(Any, log)
            if new_status == "taken":
                log_any.intake_datetime = datetime.now()
            else:
                log_any.intake_datetime = None

            await log.save()

            # 같은 (drug, slot) 중복 로그도 함께 업데이트
            await log.fetch_related("prescription", "prescription__drug")
            drug = getattr(log.prescription, "drug", None)
            drug_name = getattr(drug, "name", "") if drug else ""
            if drug_name:
                siblings = (
                    await MedicationIntakeLog.filter(
                        prescription__user_id=user_id,
                        intake_date=log.intake_date,
                        slot_label=log.slot_label,
                    )
                    .select_related("prescription", "prescription__drug")
                    .all()
                )
                for sib in siblings:
                    sib_drug = getattr(getattr(sib, "prescription", None), "drug", None)
                    if sib.id != log.id and getattr(sib_drug, "name", "") == drug_name:
                        sib.status = new_status
                        sib_any = cast(Any, sib)
                        sib_any.intake_datetime = log_any.intake_datetime
                        await sib.save()

            day = await self.get_day_detail(user_id=user_id, date=log.intake_date.isoformat())
            await cache_delete("dashboard", user_id, str(log.intake_date))
            return {"log_id": log_id, "updated": True, "day": day}

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("update_log failed")
            raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.") from e
