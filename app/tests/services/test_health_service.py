from __future__ import annotations

from tortoise.contrib.test import TestCase

from app.models.health import HealthChecklistLog, HealthChecklistTemplate
from app.models.users import User
from app.services.health import HealthService


async def _make_user(email: str) -> User:
    return await User.create(email=email, name="테스터", phone_number="01011112222", birthday="1990-01-01")


async def _make_template(label: str = "물 마시기") -> HealthChecklistTemplate:
    return await HealthChecklistTemplate.create(label=label, is_active=True)


class TestHealthService(TestCase):
    async def test_list_history_empty(self):
        user = await _make_user("health_hist@example.com")
        service = HealthService()
        result = await service.list_history(user.id, "2024-01-01", "2024-01-03")
        assert "items" in result
        assert len(result["items"]) == 3

    async def test_list_history_invalid_date(self):
        from fastapi import HTTPException

        user = await _make_user("health_inv@example.com")
        service = HealthService()
        with self.assertRaises(HTTPException) as ctx:
            await service.list_history(user.id, "2024-01-10", "2024-01-01")
        assert ctx.exception.status_code == 400

    async def test_get_day_detail_no_templates(self):
        user = await _make_user("health_notempl@example.com")
        service = HealthService()
        result = await service.get_day_detail(user.id, "2024-01-01")
        assert result["date"] == "2024-01-01"
        assert result["items"] == []
        assert result["bucket"] == "none"

    async def test_get_day_detail_with_template(self):
        user = await _make_user("health_templ@example.com")
        await _make_template("스트레칭")
        service = HealthService()
        result = await service.get_day_detail(user.id, "2024-01-01")
        assert len(result["items"]) == 1
        assert result["items"][0]["label"] == "스트레칭"
        assert result["items"][0]["status"] == "skipped"

    async def test_get_day_detail_invalid_date(self):
        from fastapi import HTTPException

        user = await _make_user("health_invdate@example.com")
        service = HealthService()
        with self.assertRaises(HTTPException) as ctx:
            await service.get_day_detail(user.id, "not-a-date")
        assert ctx.exception.status_code == 400

    async def test_update_log_done(self):
        from app.dtos.health import HealthLogUpdateRequest

        user = await _make_user("health_upd@example.com")
        tmpl = await _make_template("걷기")
        log = await HealthChecklistLog.create(user=user, template=tmpl, date="2024-01-01", status="skipped")

        service = HealthService()
        result = await service.update_log(user.id, log.id, HealthLogUpdateRequest(status="done"))
        assert result["updated"] is True
        assert result["day"]["items"][0]["status"] == "done"

    async def test_update_log_not_found(self):
        from fastapi import HTTPException

        from app.dtos.health import HealthLogUpdateRequest

        user = await _make_user("health_notfound@example.com")
        service = HealthService()
        with self.assertRaises(HTTPException) as ctx:
            await service.update_log(user.id, 9999, HealthLogUpdateRequest(status="done"))
        assert ctx.exception.status_code == 404

    async def test_seed_day_idempotent(self):
        """같은 날 두 번 seed해도 중복 생성 안 됨"""
        user = await _make_user("health_idem@example.com")
        await _make_template("명상")
        service = HealthService()
        await service._seed_day_if_empty(user_id=user.id, date_str="2024-01-01")
        await service._seed_day_if_empty(user_id=user.id, date_str="2024-01-01")
        count = await HealthChecklistLog.filter(user_id=user.id, date="2024-01-01").count()
        assert count == 1
