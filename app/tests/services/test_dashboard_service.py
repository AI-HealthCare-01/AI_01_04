from __future__ import annotations

from datetime import date, timedelta

from tortoise.contrib.test import TestCase

from app.models.diseases import Disease
from app.models.drugs import Drug
from app.models.prescriptions import MedicationIntakeLog, Prescription
from app.models.users import User
from app.services.dashboard import DashboardService


async def _make_user(email: str) -> User:
    return await User.create(email=email, name="테스터", phone_number="01011112222", birthday="1990-01-01")


class TestDashboardService(TestCase):
    async def test_summary_no_prescriptions(self):
        user = await _make_user("dash_empty@example.com")
        service = DashboardService()
        result = await service.get_summary(user)
        assert result["recent_prescription"] is None
        assert result["remaining_medication_days"] == 0
        assert result["today_medication_completed"] is False

    async def test_summary_with_prescription(self):
        user = await _make_user("dash_pres@example.com")
        drug = await Drug.create(name="테스트약")
        disease = await Disease.create(name="테스트병")
        today = date.today()
        await Prescription.create(
            user=user,
            drug=drug,
            disease=disease,
            start_date=today,
            end_date=today + timedelta(days=7),
            dose_count=1,
            dose_amount="1",
            dose_unit="정",
        )
        service = DashboardService()
        result = await service.get_summary(user)
        assert result["recent_prescription"] is not None
        assert result["recent_prescription"]["drug_name"] == "테스트약"
        assert result["remaining_medication_days"] == 7

    async def test_summary_today_medication_completed(self):
        user = await _make_user("dash_taken@example.com")
        drug = await Drug.create(name="완료약")
        today = date.today()
        pres = await Prescription.create(
            user=user,
            drug=drug,
            start_date=today,
            end_date=today,
            dose_count=1,
            dose_amount="1",
            dose_unit="정",
        )
        await MedicationIntakeLog.create(
            prescription=pres,
            intake_date=today,
            slot_label="아침",
            status="taken",
        )
        service = DashboardService()
        result = await service.get_summary(user)
        assert result["today_medication_completed"] is True

    async def test_summary_today_medication_not_completed(self):
        user = await _make_user("dash_skip@example.com")
        drug = await Drug.create(name="미완료약")
        today = date.today()
        pres = await Prescription.create(
            user=user,
            drug=drug,
            start_date=today,
            end_date=today,
            dose_count=1,
            dose_amount="1",
            dose_unit="정",
        )
        await MedicationIntakeLog.create(
            prescription=pres,
            intake_date=today,
            slot_label="아침",
            status="skipped",
        )
        service = DashboardService()
        result = await service.get_summary(user)
        assert result["today_medication_completed"] is False

    async def test_summary_list_by_intake_date_failure_fallback(self):
        """list_by_intake_date 실패 시 today_logs=[] fallback"""
        from unittest.mock import AsyncMock, patch

        user = await _make_user("dash_fallback@example.com")
        service = DashboardService()
        with patch.object(
            service.medication_repo,
            "list_by_intake_date",
            new=AsyncMock(side_effect=Exception("DB error")),
        ):
            result = await service.get_summary(user)
        assert result["today_medication_completed"] is False

    async def test_get_summary_impl_exception_raises_http(self):
        """_get_summary_impl 실패 시 HTTPException 500"""
        from unittest.mock import AsyncMock, patch

        from fastapi import HTTPException

        user = await _make_user("dash_err@example.com")
        service = DashboardService()
        with patch.object(
            service,
            "_get_summary_impl",
            new=AsyncMock(side_effect=Exception("unexpected")),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await service.get_summary(user)
        assert ctx.exception.status_code == 500
