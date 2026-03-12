"""챗봇 도메인 Repository.

ChatbotSession, ChatbotMessage, ChatbotSessionSummary 조회/생성을 담당한다.
항상 user_id 스코프로 다른 사용자 세션/메시지 접근을 차단한다.
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
<<<<<<< HEAD
        """
        user_id 소유의 세션만 단건 조회한다.

        Args:
            user_id (int):
                인증된 사용자 ID
            session_id (int):
                조회할 세션 ID

        Returns:
            ChatbotSession | None:
                세션 객체, 없거나 소유자가 다르면 None
=======
        """user_id 소유의 챗봇 세션을 단건 조회한다.

        Args:
            user_id (int): 소유자 사용자 ID.
            session_id (int): 조회할 세션 ID.

        Returns:
            ChatbotSession | None: ChatbotSession 객체. 없거나 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
>>>>>>> develop
        """
        return await self._session_model.get_or_none(id=session_id, user_id=user_id)

    async def list_sessions_by_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatbotSession]:
<<<<<<< HEAD
        """
        사용자의 세션 목록을 최신순으로 조회한다.

        Args:
            user_id (int):
                인증된 사용자 ID
            limit (int):
                최대 조회 건수 (기본값: 50)
            offset (int):
                조회 시작 오프셋 (기본값: 0)

        Returns:
            list[ChatbotSession]:
                세션 목록 (started_at 내림차순)
=======
        """사용자의 챗봇 세션 목록을 최신순으로 조회한다.

        Args:
            user_id (int): 조회할 사용자 ID.
            limit (int): 최대 반환 건수. 기본값 50.
            offset (int): 건너뛸 건수. 기본값 0.

        Returns:
            list[ChatbotSession]: ChatbotSession 목록 (started_at 내림차순).

        Raises:
            OperationalError: DB 연결 오류 시.
>>>>>>> develop
        """
        return await self._session_model.filter(user_id=user_id).order_by("-started_at").offset(offset).limit(limit)

    async def list_sessions_by_date_range(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[ChatbotSession]:
<<<<<<< HEAD
        """
        날짜 범위 내 세션 목록을 조회한다.

        Args:
            user_id (int):
                인증된 사용자 ID
            from_dt (datetime):
                조회 시작 일시 (inclusive)
            to_dt (datetime):
                조회 종료 일시 (inclusive)

        Returns:
            list[ChatbotSession]:
                세션 목록 (started_at 오름차순)
=======
        """기간 내 챗봇 세션 목록을 조회한다 (started_at 기준).

        Args:
            user_id (int): 조회할 사용자 ID.
            from_dt (datetime): 조회 시작 시각 (포함).
            to_dt (datetime): 조회 종료 시각 (포함).

        Returns:
            list[ChatbotSession]: 기간 내 ChatbotSession 목록 (시간 오름차순).

        Raises:
            OperationalError: DB 연결 오류 시.
>>>>>>> develop
        """
        return await self._session_model.filter(
            user_id=user_id,
            started_at__gte=from_dt,
            started_at__lte=to_dt,
        ).order_by("started_at")

    async def create_session(self, user_id: int) -> ChatbotSession:
<<<<<<< HEAD
        """
        새 챗봇 세션을 생성한다.

        Args:
            user_id (int):
                인증된 사용자 ID

        Returns:
            ChatbotSession:
                생성된 세션 객체
=======
        """새 챗봇 세션을 생성한다.

        Args:
            user_id (int): 소유자 사용자 ID.

        Returns:
            ChatbotSession: 생성된 ChatbotSession 객체.

        Raises:
            OperationalError: DB 연결 오류 시.
>>>>>>> develop
        """
        return await self._session_model.create(user_id=user_id)

    async def end_session(self, user_id: int, session_id: int) -> ChatbotSession | None:
<<<<<<< HEAD
        """
        세션을 종료한다 (ended_at 업데이트).

        Args:
            user_id (int):
                인증된 사용자 ID
            session_id (int):
                종료할 세션 ID

        Returns:
            ChatbotSession | None:
                종료된 세션 객체, 세션이 없거나 소유자가 다르면 None
=======
        """챗봇 세션을 종료한다 (ended_at을 현재 시각으로 설정).

        Args:
            user_id (int): 소유자 사용자 ID.
            session_id (int): 종료할 세션 ID.

        Returns:
            ChatbotSession | None: 업데이트된 ChatbotSession 객체. 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
>>>>>>> develop
        """
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
<<<<<<< HEAD
        """
        세션의 메시지 목록을 조회한다 (user 소유 검증 포함).

        Args:
            user_id (int):
                인증된 사용자 ID
            session_id (int):
                조회할 세션 ID
            limit (int):
                최대 조회 건수 (기본값: 100)

        Returns:
            list[ChatbotMessage]:
                메시지 목록 (created_at 오름차순)
=======
        """세션의 메시지 목록을 조회한다 (session이 user 소유인지 검증).

        Args:
            user_id (int): 소유자 사용자 ID.
            session_id (int): 조회할 세션 ID.
            limit (int): 최대 반환 건수. 기본값 100.

        Returns:
            list[ChatbotMessage]: ChatbotMessage 목록 (created_at 오름차순).

        Raises:
            OperationalError: DB 연결 오류 시.
>>>>>>> develop
        """
        return (
            await self._message_model.filter(
                session_id=session_id,
                session__user_id=user_id,
            )
            .order_by("created_at")
            .limit(limit)
        )

    async def add_message(
        self,
        user_id: int,
        session_id: int,
        *,
        sender: str,
        message: str,
    ) -> ChatbotMessage | None:
<<<<<<< HEAD
        """
        세션에 메시지를 추가한다.

        Args:
            user_id (int):
                인증된 사용자 ID
            session_id (int):
                메시지를 추가할 세션 ID
            sender (str):
                발신자 구분 ('user' 또는 'assistant')
            message (str):
                메시지 내용

        Returns:
            ChatbotMessage | None:
                생성된 메시지 객체, 세션이 없거나 소유자가 다르면 None
=======
        """세션에 메시지를 추가한다 (session이 user 소유인지 검증).

        Args:
            user_id (int): 소유자 사용자 ID.
            session_id (int): 메시지를 추가할 세션 ID.
            sender (str): 발신자 (user 또는 assistant).
            message (str): 메시지 내용.

        Returns:
            ChatbotMessage | None: 생성된 ChatbotMessage 객체. 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
>>>>>>> develop
        """
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
<<<<<<< HEAD
        """
        세션 종료 후 AI 요약을 저장한다.

        Args:
            user_id (int):
                인증된 사용자 ID
            session_id (int):
                요약을 저장할 세션 ID
            summary (str):
                AI가 생성한 대화 요약 내용

        Returns:
            ChatbotSessionSummary | None:
                생성된 요약 객체, 세션이 없거나 소유자가 다르면 None
=======
        """세션에 AI 요약을 추가한다 (session이 user 소유인지 검증).

        Args:
            user_id (int): 소유자 사용자 ID.
            session_id (int): 요약을 추가할 세션 ID.
            summary (str): AI가 생성한 대화 요약 내용.

        Returns:
            ChatbotSessionSummary | None: 생성된 ChatbotSessionSummary 객체. 소유자가 다르면 None.

        Raises:
            OperationalError: DB 연결 오류 시.
>>>>>>> develop
        """
        session = await self.get_session_for_user(user_id, session_id)
        if not session:
            return None
        return await self._summary_model.create(session=session, summary=summary)
