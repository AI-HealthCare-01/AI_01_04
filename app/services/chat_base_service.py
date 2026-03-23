from __future__ import annotations

import logging

from app.models.chat_health import HealthChat
from app.models.chat_medication import MediChat
from app.models.chatbot import ChatbotMessage
from app.models.users import User
from app.repositories.chatbot_repository import ChatbotRepository
from app.utils.constants import RECENT_CONVERSATION_LIMIT

logger = logging.getLogger(__name__)


class ChatBaseService:
    def __init__(self) -> None:
        self.chatbot_repo = ChatbotRepository()

    async def check_user_exists(self, patient_id: str) -> bool:
        return await User.filter(id=patient_id).exists()

    # ── 레거시 이력 조회 (하위호환) ──

    async def get_health_history(self, patient_id: str) -> list[dict]:
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
        medi_history = await MediChat.filter(patient_id=patient_id).all()
        return [
            {
                "created_at": h.created_at,
                "medications": h.medications,
                "disease_code": h.disease_code,
            }
            for h in medi_history
        ]

    # ── 세션 기반 대화 맥락 ──

    def build_conversation_context(self, messages: list[ChatbotMessage]) -> str:
        """세션 메시지를 대화 맥락 문자열로 변환한다."""
        recent = messages[-RECENT_CONVERSATION_LIMIT * 2 :]  # user+assistant 쌍
        if not recent:
            return ""
        lines: list[str] = []
        for msg in recent:
            role = "사용자" if msg.sender == "user" else "AI"
            text = msg.message[:200] if msg.sender == "assistant" else msg.message
            lines.append(f"{role}: {text}")
        return "\n".join(lines)
