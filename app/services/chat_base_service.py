from __future__ import annotations

import logging

from app.models.chat_health import HealthChat
from app.models.chat_medication import MediChat
from app.models.chatbot import ChatbotMessage
from app.models.users import User
from app.repositories.chatbot_repository import ChatbotRepository
from app.services.chat_openai_service import ChatOpenaiService
from app.utils.constants import RECENT_CONVERSATION_LIMIT, SUMMARY_TRIGGER_THRESHOLD

logger = logging.getLogger(__name__)


class ChatBaseService:
    def __init__(self) -> None:
        self.chatbot_repo = ChatbotRepository()
        self._summary_ai = ChatOpenaiService()

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

    async def maybe_summarize_and_rotate(self, session_id: int, user_id: int, mode: str) -> None:
        """메시지가 임계값 이상이면 요약 생성 → 저장 → 세션 종료."""
        messages = await self.chatbot_repo.get_messages(session_id, limit=SUMMARY_TRIGGER_THRESHOLD + 1)
        if len(messages) < SUMMARY_TRIGGER_THRESHOLD:
            return

        conversation = "\n".join(
            f"{'사용자' if m.sender == 'user' else 'AI'}: {m.message[:300]}" for m in messages
        )
        system = "아래 대화를 핵심 내용 위주로 3~5문장으로 요약하세요. 환자의 주요 증상, 질문, AI 답변 핵심만 포함하세요."
        result = await self._summary_ai.get_advice(system, conversation)
        summary = result.get("chat_answer", "")

        if summary:
            await self.chatbot_repo.save_summary(session_id, summary)
            await self.chatbot_repo.end_session(session_id)
            logger.info("세션 %d 요약 완료 → 새 세션으로 전환", session_id)
