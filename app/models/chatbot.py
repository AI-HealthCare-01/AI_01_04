"""
챗봇 세션/메시지 모델 (ERD 기반)

📚 학습 포인트:
- 세션 → 메시지: 1:N (한 대화에 여러 메시지)
- sender: 'user' 또는 'assistant' (누가 보냈는지)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

if TYPE_CHECKING:
    from app.models.users import User


class ChatbotSession(models.Model):
    """
    챗봇 대화 세션 (ERD: chatbot_sessions)
    """
    id = fields.IntField(pk=True)
    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="chatbot_sessions",
    )
    started_at = fields.DatetimeField(null=True)
    ended_at = fields.DatetimeField(null=True)

    class Meta:
        table = "chatbot_sessions"


class ChatbotMessage(models.Model):
    """
    챗봇 메시지 (ERD: chatbot_messages)
    """

    id = fields.IntField(pk=True)
    session: ForeignKeyRelation[ChatbotSession] = fields.ForeignKeyField(
        "models.ChatbotSession",
        on_delete=fields.CASCADE,
        related_name="messages",
    )

    sender = fields.CharField(max_length=20)  # user, assistant
    message = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chatbot_messages"


class ChatbotSessionSummary(models.Model):
    """
    세션 요약 (ERD: chatbot_session_summaries)

    대화 종료 후 AI가 생성한 요약
    """

    id = fields.IntField(pk=True)
    session: ForeignKeyRelation[ChatbotSession] = fields.ForeignKeyField(
        "models.ChatbotSession",
        on_delete=fields.CASCADE,
        related_name="summaries",
    )

    summary = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chatbot_session_summaries"