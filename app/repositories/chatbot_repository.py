"""챗봇 세션/메시지 Repository.

ChatbotSession, ChatbotMessage, ChatbotSessionSummary 조회/생성을 담당한다.
항상 user_id 스코프로 다른 사용자 세션 접근을 차단한다.
"""

from __future__ import annotations

from app.models.chatbot import ChatbotMessage, ChatbotSession, ChatbotSessionSummary


class ChatbotRepository:

    async def create_session(self, user_id: int, mode: str = "medication") -> ChatbotSession:
        return await ChatbotSession.create(user_id=user_id, mode=mode)

    async def get_session(self, user_id: int, session_id: int) -> ChatbotSession | None:
        return await ChatbotSession.get_or_none(id=session_id, user_id=user_id)

    async def get_or_create_active_session(self, user_id: int, mode: str) -> ChatbotSession:
        """종료되지 않은 최신 세션을 반환하거나 새로 생성한다."""
        session = await ChatbotSession.filter(
            user_id=user_id, mode=mode, ended_at__isnull=True,
        ).order_by("-started_at").first()
        if session:
            return session
        return await self.create_session(user_id, mode)

    async def add_message(self, session_id: int, sender: str, message: str) -> ChatbotMessage:
        return await ChatbotMessage.create(session_id=session_id, sender=sender, message=message)

    async def get_messages(self, session_id: int, limit: int = 20) -> list[ChatbotMessage]:
        """세션 내 최근 메시지를 시간순으로 반환한다."""
        msgs = (
            await ChatbotMessage.filter(session_id=session_id)
            .order_by("-created_at")
            .limit(limit)
        )
        return list(reversed(msgs))

    async def save_summary(self, session_id: int, summary: str) -> ChatbotSessionSummary:
        return await ChatbotSessionSummary.create(session_id=session_id, summary=summary)

    async def get_latest_summary(self, user_id: int, mode: str) -> str | None:
        """이전 세션의 가장 최근 요약을 반환한다."""
        session = (
            await ChatbotSession.filter(user_id=user_id, mode=mode, ended_at__isnull=False)
            .order_by("-ended_at")
            .first()
        )
        if not session:
            return None
        summary = await ChatbotSessionSummary.filter(session_id=session.id).order_by("-created_at").first()
        return summary.summary if summary else None

    async def end_session(self, session_id: int) -> None:
        from datetime import datetime

        from app.core import config
        await ChatbotSession.filter(id=session_id).update(ended_at=datetime.now(config.TIMEZONE))
