from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import-not-found]
from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

from app.core import config

logger = logging.getLogger(__name__)


class ChatOpenaiService:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=config.OPENAI_API_KEY)

    async def get_advice(self, system_content: str, user_content: str) -> dict[str, str]:
        try:
            response = self.llm.invoke([SystemMessage(content=system_content), HumanMessage(content=user_content)])
            ai_content = response.content if response.content else "답변을 생성할 수 없습니다."
            return {"chat_answer": ai_content}
        except Exception:
            logger.exception("AI Service Error")
            return {"chat_answer": "죄송합니다. 상담 중 오류가 발생했습니다."}
