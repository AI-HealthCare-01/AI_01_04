from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import-not-found]
from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

from app.core import config

logger = logging.getLogger(__name__)


class ChatOpenaiService:
    def __init__(self) -> None:
        self.llm = ChatOpenAI(model="gpt-4o-mini", api_key=config.OPENAI_API_KEY)  # type: ignore[arg-type]

    async def get_advice(self, system_content: str, user_content: str) -> dict[str, str]:
        try:
            response = self.llm.invoke(
                [SystemMessage(content=system_content), HumanMessage(content=user_content)],
                timeout=30,
            )
            ai_content: str = str(response.content) if response.content else "답변을 생성할 수 없습니다."
            return {"chat_answer": ai_content}
        except TimeoutError:
            logger.warning("AI 응답 타임아웃")
            return {"chat_answer": "응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."}
        except Exception:
            logger.exception("AI Service Error")
            return {"chat_answer": "죄송합니다. 상담 중 오류가 발생했습니다."}

    async def stream_advice(self, system_content: str, user_content: str) -> AsyncGenerator[str, None]:
        try:
            async for chunk in self.llm.astream(
                [SystemMessage(content=system_content), HumanMessage(content=user_content)],
            ):
                text = str(chunk.content) if hasattr(chunk, "content") else str(chunk)
                if text:
                    yield text
        except Exception:
            logger.exception("AI Stream Error")
            yield "죄송합니다. 상담 중 오류가 발생했습니다."
