from __future__ import annotations

from datetime import date

from tortoise.contrib.test import TestCase

from app.models.drugs import Drug
from app.models.prescriptions import MedicationIntakeLog, Prescription
from app.models.users import User
from app.services.medication import MedicationService, _calc_rate_from_logs, _slots_by_dose_count


async def _make_user(email: str) -> User:
    return await User.create(email=email, name="테스터", phone_number="01011112222", birthday="1990-01-01")


async def _make_prescription(user: User, dose_count: int = 1) -> Prescription:
    drug = await Drug.create(name=f"약_{user.id}_{dose_count}")
    return await Prescription.create(
        user=user,
        drug=drug,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        dose_count=dose_count,
        dose_amount="1",
        dose_unit="정",
    )


class TestSlotsAndRate(TestCase):
    async def test_slots_none(self):
        assert _slots_by_dose_count(None) == ["아침"]

    async def test_slots_1(self):
        assert _slots_by_dose_count(1) == ["아침"]

    async def test_slots_2(self):
        assert _slots_by_dose_count(2) == ["아침", "저녁"]

    async def test_slots_3(self):
        assert _slots_by_dose_count(3) == ["아침", "점심", "저녁"]

    async def test_slots_4(self):
        assert _slots_by_dose_count(4) == ["아침", "점심", "저녁", "자기전"]

    async def test_calc_rate_empty(self):
        assert _calc_rate_from_logs([]) == 0


class TestMedicationService(TestCase):
    async def test_list_history_empty(self):
        user = await _make_user("med_hist@example.com")
        service = MedicationService()
        result = await service.list_history(user.id, "2024-01-01", "2024-01-03")
        assert "items" in result
        assert "meta" in result
        assert result["meta"]["total"] == 3

    async def test_list_history_invalid_date(self):
        from fastapi import HTTPException

        user = await _make_user("med_inv@example.com")
        service = MedicationService()
        with self.assertRaises(HTTPException) as ctx:
            await service.list_history(user.id, "2024-01-10", "2024-01-01")
        assert ctx.exception.status_code == 400

    async def test_list_history_with_prescription(self):
        user = await _make_user("med_pres@example.com")
        await _make_prescription(user, dose_count=2)
        service = MedicationService()
        result = await service.list_history(user.id, "2024-01-01", "2024-01-01")
        assert len(result["items"]) == 1
        assert result["items"][0]["bucket"] == "bad"  # 모두 skipped → 0%

    async def test_list_history_sort_asc(self):
        user = await _make_user("med_asc@example.com")
        service = MedicationService()
        result = await service.list_history(user.id, "2024-01-01", "2024-01-03", sort="asc")
        dates = [item["date"] for item in result["items"]]
        assert dates == sorted(dates)

    async def test_get_day_detail_empty(self):
        user = await _make_user("med_day@example.com")
        service = MedicationService()
        result = await service.get_day_detail(user.id, "2024-01-01")
        assert result["date"] == "2024-01-01"
        assert result["items"] == []
        assert result["bucket"] == "none"

    async def test_get_day_detail_with_prescription(self):
        user = await _make_user("med_daypres@example.com")
        await _make_prescription(user, dose_count=1)
        service = MedicationService()
        result = await service.get_day_detail(user.id, "2024-01-01")
        assert len(result["items"]) == 1
        assert result["items"][0]["status"] == "skipped"

    async def test_get_day_detail_invalid_date(self):
        from fastapi import HTTPException

        user = await _make_user("med_invdate@example.com")
        service = MedicationService()
        with self.assertRaises(HTTPException) as ctx:
            await service.get_day_detail(user.id, "not-a-date")
        assert ctx.exception.status_code == 400

    async def test_update_log_taken(self):
        from app.dtos.medication import MedicationLogUpdateRequest

        user = await _make_user("med_upd@example.com")
        pres = await _make_prescription(user)
        log = await MedicationIntakeLog.create(
            prescription=pres, intake_date=date(2024, 1, 1), slot_label="아침", status="skipped"
        )
        service = MedicationService()
        result = await service.update_log(user.id, log.id, MedicationLogUpdateRequest(status="taken"))
        assert result["updated"] is True
        assert result["day"]["items"][0]["status"] == "taken"

    async def test_update_log_not_found(self):
        from fastapi import HTTPException

        from app.dtos.medication import MedicationLogUpdateRequest

        user = await _make_user("med_notfound@example.com")
        service = MedicationService()
        with self.assertRaises(HTTPException) as ctx:
            await service.update_log(user.id, 9999, MedicationLogUpdateRequest(status="taken"))
        assert ctx.exception.status_code == 404

    async def test_seed_day_idempotent(self):
        user = await _make_user("med_idem@example.com")
        await _make_prescription(user)
        service = MedicationService()
        await service._seed_day_if_empty(user_id=user.id, date_str="2024-01-01")
        await service._seed_day_if_empty(user_id=user.id, date_str="2024-01-01")
        count = await MedicationIntakeLog.filter(prescription__user_id=user.id, intake_date="2024-01-01").count()
        assert count == 1
