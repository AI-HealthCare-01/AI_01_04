from __future__ import annotations

import logging

from app.models.chat_health import HealthChat
from app.models.chat_medication import MediChat
from app.models.users import User

logger = logging.getLogger(__name__)


class ChatBaseService:
    async def check_user_exists(self, patient_id: str) -> bool:
        return await User.filter(id=patient_id).exists()

    async def get_health_history(self, patient_id: str) -> list[dict]:
        """건강 상담 이력 조회."""
        logger.debug("건강 상담 이력 DB 조회: patient_id=%s", patient_id)
        health_history = await HealthChat.filter(patient_id=patient_id).all()
        return [
            {
                "created_at": h.created_at,
                "user_question": h.user_question,
                "advice": h.advice,
            }
            for h in health_history
        ]

    async def get_medi_history(self, patient_id: str) -> list[dict]:
        """복약 이력 조회."""
        logger.debug("복약 이력 DB 조회: patient_id=%s", patient_id)
        medi_history = await MediChat.filter(patient_id=patient_id).all()
        return [
            {
                "created_at": h.created_at,
                "medications": h.medications,
                "disease_code": h.disease_code,
            }
            for h in medi_history
        ]
