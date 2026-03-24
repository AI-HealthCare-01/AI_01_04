"""건강관리 체크리스트 서비스.

일자별 체크리스트 시드(seed) 및 조회, 달성률 계산, 로그 업데이트를 담당한다.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast

from fastapi import HTTPException
from starlette import status

from app.dtos.health import HealthLogUpdateRequest
from app.models.health import HealthChecklistLog
from app.models.recommendations import UserActiveRecommendation
from app.repositories.health_repository import HealthRepository
from app.utils.cache import cache_delete
from app.utils.datetime import DateTimeError, date_range_inclusive, normalize_from_to, parse_date_yyyy_mm_dd
from app.utils.progress import rate_bucket


def _calc_rate_from_logs(logs: list[HealthChecklistLog]) -> int:
    """체크리스트 로그에서 done 비율(%)을 계산한다.

    Args:
        logs (list[HealthChecklistLog]): 계산할 로그 목록.

    Returns:
        int: done 비율 (0~100).
    """
    if not logs:
        return 0
    done = sum(1 for lg in logs if lg.status == "done")
    return int(round((done / len(logs)) * 100))


class HealthService:
    def __init__(self):
        self.health_repo = HealthRepository()

    async def ensure_day_seed(self, *, user_id: int, date: str) -> None:
        """외부 서비스에서 호출하는 시드 진입점."""
        await self._seed_day_if_empty(user_id=user_id, date_str=date)

    @staticmethod
    async def _earliest_scan_date(user_id: int) -> date | None:
        """사용자의 가장 오래된 처방 start_date를 반환한다."""
        from app.models.prescriptions import Prescription
        row = await Prescription.filter(
            user_id=user_id, start_date__isnull=False
        ).order_by("start_date").first()
        return row.start_date if row else None

    async def _get_user_active_labels(self, user_id: int) -> list[str]:
        """사용자의 활성 추천 목표 content 목록을 반환한다."""
        actives = await UserActiveRecommendation.filter(user_id=user_id).prefetch_related("recommendation")
        labels: list[str] = []
        seen: set[str] = set()
        for ar in actives:
            rec = ar.recommendation
            content = (rec.content or "").strip() if rec else ""
            if content and content not in seen:
                seen.add(content)
                labels.append(content)
        return labels

    async def _seed_day_if_empty(self, *, user_id: int, date_str: str) -> None:
        """해당 날짜에 로그가 없으면 사용자 활성 추천 목표 → 디폴트 템플릿 순으로 시드한다.

        이미 로그가 있으면 아무것도 하지 않아 멱등성을 보장한다.

        Args:
            user_id (int): 시드를 생성할 사용자 ID.
            date_str (str): 시드를 생성할 날짜 (YYYY-MM-DD).
        """
        d = parse_date_yyyy_mm_dd(date_str)

        existing_cnt = await HealthChecklistLog.filter(user_id=user_id, date=d).count()
        if existing_cnt > 0:
            return

        # 1) 사용자 활성 추천 목표 기반 시드
        active_labels = await self._get_user_active_labels(user_id)
        if active_labels:
            templates = await self.health_repo.list_active_templates()
            tpl_map = {t.label: t for t in templates} if templates else {}

            logs_to_create: list[HealthChecklistLog] = []
            for label in active_labels:
                tpl = tpl_map.get(label)
                logs_to_create.append(
                    HealthChecklistLog(
                        user_id=user_id,
                        template_id=tpl.id if tpl else None,
                        date=d,
                        status="skipped",
                        checked_at=None,
                        label_override=label if not tpl else None,
                    )
                )
            if logs_to_create:
                await HealthChecklistLog.bulk_create(logs_to_create)
                return

        # 2) 활성 추천 목표가 없으면 시드하지 않음
        return

    async def list_history(self, user_id: int, date_from: str | None, date_to: str | None) -> dict:
        """기간별 건강관리 이력을 조회한다 (날짜 내림차순).

        Args:
            user_id (int): 조회할 사용자 ID.
            date_from (str | None): 조회 시작일 (YYYY-MM-DD). None이면 30일 전.
            date_to (str | None): 조회 종료일 (YYYY-MM-DD). None이면 오늘.

        Returns:
            dict: items 키에 날짜별 달성률 목록이 담긴 딕셔너리.

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
        """특정 날짜의 체크리스트 상세를 조회한다 (없으면 시드 후 반환).

        Args:
            user_id (int): 조회할 사용자 ID.
            date (str): 조회할 날짜 (YYYY-MM-DD).

        Returns:
            dict: date, rate, bucket, items가 담긴 딕셔너리.

        Raises:
            HTTPException: 날짜 형식 오류 시 400.
        """
        try:
            d = parse_date_yyyy_mm_dd(date)
        except DateTimeError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        await self._seed_day_if_empty(user_id=user_id, date_str=date)

        logs = await self.health_repo.list_logs_by_user_date(user_id=user_id, dt=d)

        items: list[dict] = []
        for lg in logs:
            label = lg.label_override or (lg.template.label if lg.template else "")
            items.append(
                {
                    "id": lg.id,
                    "label": label,
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
        """건강관리 로그 상태를 업데이트한다 (done/skipped).

        Args:
            user_id (int): 소유자 사용자 ID.
            log_id (int): 업데이트할 로그 ID.
            data (HealthLogUpdateRequest): 새 상태가 담긴 요청 데이터.

        Returns:
            dict: log_id, updated, day가 담긴 딕셔너리.

        Raises:
            HTTPException: 로그가 없거나 소유자가 다를 시 404.
        """
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
        await cache_delete("dashboard", user_id, str(log.date))
        return {"log_id": log_id, "updated": True, "day": day}
