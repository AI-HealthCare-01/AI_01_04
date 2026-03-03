"""
챗봇 도메인 Repository

- ChatbotSession, ChatbotMessage, ChatbotSessionSummary
- 항상 user_id 스코프: 다른 사용자 세션/메시지 조회 불가
"""

from __future__ import annotations

from datetime import datetime

from app.models.chatbot import ChatbotMessage, ChatbotSession, ChatbotSessionSummary


class ChatbotRepository:
    def __init__(self):
        self._session_model = ChatbotSession
        self._message_model = ChatbotMessage
        self._summary_model = ChatbotSessionSummary

    async def get_session_for_user(self, user_id: int, session_id: int) -> ChatbotSession | None:
        """user_id 소유의 세션만 조회"""
        return await self._session_model.get_or_none(id=session_id, user_id=user_id)

    async def list_sessions_by_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatbotSession]:
        return (
            await self._session_model.filter(user_id=user_id)
            .order_by("-started_at")
            .offset(offset)
            .limit(limit)
        )

    async def list_sessions_by_date_range(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[ChatbotSession]:
        return await self._session_model.filter(
            user_id=user_id,
            started_at__gte=from_dt,
            started_at__lte=to_dt,
        ).order_by("started_at")

    async def create_session(self, user_id: int) -> ChatbotSession:
        return await self._session_model.create(user_id=user_id)

    async def end_session(self, user_id: int, session_id: int) -> ChatbotSession | None:
        session = await self.get_session_for_user(user_id, session_id)
        if not session:
            return None
        from app.core import config

        session.ended_at = datetime.now(config.TIMEZONE)
        await session.save(update_fields=["ended_at"])
        return session

    async def get_messages_for_user(
        self,
        user_id: int,
        session_id: int,
        *,
        limit: int = 100,
    ) -> list[ChatbotMessage]:
        """세션의 메시지 목록 (session이 user 소유인지 검증)"""
        return await self._message_model.filter(
            session_id=session_id,
            session__user_id=user_id,
        ).order_by("created_at").limit(limit)

    async def add_message(
        self,
        user_id: int,
        session_id: int,
        *,
        sender: str,
        message: str,
    ) -> ChatbotMessage | None:
        session = await self.get_session_for_user(user_id, session_id)
        if not session:
            return None
        return await self._message_model.create(session=session, sender=sender, message=message)

    async def add_summary(
        self,
        user_id: int,
        session_id: int,
        *,
        summary: str,
    ) -> ChatbotSessionSummary | None:
        session = await self.get_session_for_user(user_id, session_id)
        if not session:
            return None
        return await self._summary_model.create(session=session, summary=summary)
