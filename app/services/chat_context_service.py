"""챗봇 사용자 컨텍스트 조회 서비스.

active 판단 기준:
  - 총 처방량(dose_count × 처방일수)과 실제 복용(taken) 횟수를 비교
  - 남은 약 > 0 이면 active (end_date가 지나도 약이 남아있으면 계속 active)
  - dose_count/start_date/end_date 정보가 불완전하면 일단 active로 간주
deactivate:
  - 사용자가 챗봇에서 직접 "다 먹었다" 처리 → end_date를 어제로 설정 + 남은 로그 없음으로 판단
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.models.prescriptions import MedicationIntakeLog, Prescription
from app.models.scans import Scan


class ChatContextService:
    async def _calc_remaining(self, rx: Prescription) -> int | None:
        """남은 약 개수를 계산한다. 계산 불가하면 None (= active로 간주)."""
        if not rx.dose_count or not rx.start_date or not rx.end_date:
            return None

        total_days = (rx.end_date - rx.start_date).days + 1
        total_doses = rx.dose_count * total_days

        taken_count = await MedicationIntakeLog.filter(prescription_id=rx.id, status="taken").count()

        return max(total_doses - taken_count, 0)

    async def _is_active(self, rx: Prescription) -> bool:
        """남은 약이 있으면 active. 계산 불가하면 active로 간주."""
        remaining = await self._calc_remaining(rx)
        if remaining is None:
            return True
        return remaining > 0

    async def get_user_context(self, user_id: int) -> dict[str, Any]:
        diseases = await self._get_user_diseases(user_id)
        medications = await self._get_active_medications(user_id)
        scan_summary = await self._get_scan_summary(user_id)

        return {
            "user_id": user_id,
            "diseases": diseases,
            "medications": medications,
            "scan_summary": scan_summary,
            "has_diseases": len(diseases) > 0,
            "has_medications": len(medications) > 0,
            "has_scans": scan_summary["total"] > 0,
        }

    async def _get_user_diseases(self, user_id: int) -> list[dict[str, Any]]:
        prescriptions = await Prescription.filter(user_id=user_id).all()

        seen: set[int] = set()
        diseases: list[dict[str, Any]] = []
        for rx in prescriptions:
            if not await self._is_active(rx):
                continue
            await rx.fetch_related("disease")
            if rx.disease and rx.disease.id not in seen:
                seen.add(rx.disease.id)
                diseases.append(
                    {
                        "id": rx.disease.id,
                        "name": rx.disease.name,
                        "kcd_code": rx.disease.kcd_code,
                    }
                )
        return diseases

    async def _get_active_medications(self, user_id: int) -> list[dict[str, Any]]:
        prescriptions = await Prescription.filter(user_id=user_id).all()

        meds: list[dict[str, Any]] = []
        seen_drug_ids: set[int] = set()
        for rx in prescriptions:
            if not await self._is_active(rx):
                continue

            await rx.fetch_related("drug")
            if rx.drug:
                if rx.drug.id in seen_drug_ids:
                    continue
                seen_drug_ids.add(rx.drug.id)
                drug_name = rx.drug.name
            else:
                drug_name = "미등록 약품"

            remaining = await self._calc_remaining(rx)

            meds.append(
                {
                    "prescription_id": rx.id,
                    "drug_name": drug_name,
                    "dose_count": rx.dose_count,
                    "dose_amount": rx.dose_amount,
                    "start_date": str(rx.start_date) if rx.start_date else None,
                    "end_date": str(rx.end_date) if rx.end_date else None,
                    "remaining": remaining,
                }
            )
        return meds

    async def _get_scan_summary(self, user_id: int) -> dict[str, Any]:
        scans = await Scan.filter(user_id=user_id).order_by("-created_at").limit(10)
        total = await Scan.filter(user_id=user_id).count()

        pending = [s for s in scans if s.status in ("uploaded", "processing")]
        completed = [s for s in scans if s.status in ("done", "updated", "saved")]

        return {
            "total": total,
            "pending_count": len(pending),
            "completed_count": len(completed),
            "latest_scan_status": scans[0].status if scans else None,
        }

    async def deactivate_prescription(self, user_id: int, prescription_id: int) -> bool:
        """사용자가 '다 먹었다' 처리. end_date를 어제로 당긴다."""
        rx = await Prescription.get_or_none(id=prescription_id, user_id=user_id)
        if not rx:
            return False
        rx.end_date = date.today() - timedelta(days=1)
        await rx.save(update_fields=["end_date"])
        return True

    def build_context_prompt(self, context: dict[str, Any]) -> str:
        lines: list[str] = []

        if context["diseases"]:
            lines.append("[등록된 질병]")
            for d in context["diseases"]:
                code_str = f" ({d['kcd_code']})" if d.get("kcd_code") else ""
                lines.append(f"  - {d['name']}{code_str}")

        if context["medications"]:
            lines.append("[현재 복용 중인 약품]")
            for m in context["medications"]:
                parts = [m["drug_name"]]
                if m.get("dose_count"):
                    parts.append(f"1일 {m['dose_count']}회")
                if m.get("remaining") is not None:
                    parts.append(f"남은 약 {m['remaining']}회분")
                lines.append(f"  - {', '.join(parts)}")

        if not lines:
            lines.append("[등록된 질병/약품 정보 없음]")

        return "\n".join(lines)
