import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore[import-not-found]
from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]


class ChatOpenaiService:
    def __init__(self):
        # .env 파일의 환경 변수 로드
        load_dotenv()

        self.llm = ChatOpenAI(model="gpt-4o-mini", openai_api_key=os.getenv("OPENAI_API_KEY"))

    async def get_advice(self, system_content: str, user_content: str):
        try:
            response = self.llm.invoke([SystemMessage(content=system_content), HumanMessage(content=user_content)])

            # response.content 체크
            ai_content = response.content if response.content else "답변을 생성할 수 없습니다."
            return {"chat_answer": ai_content}

        except Exception as e:
            # 모든 에러를 캐치하여 서버 중단을 방지합니다.
            print(f"AI Service Error: {e}")
            return {"chat_answer": f"죄송합니다. 상담 중 오류가 발생했습니다. (사유: {str(e)})"}
