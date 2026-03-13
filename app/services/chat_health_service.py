from ..models.chat_health import HealthChat
from ..schemas.chat import ChatRequest
from ..utils.constants import COMMON_SYSTEM_PROMPT
from .chat_base_service import ChatBaseService as BaseService
from .chat_openai_service import ChatOpenaiService as OpenAI


class ChatHealthService(BaseService):
    def __init__(self):
        super().__init__()
        self.ai = OpenAI()

    async def process_health_chat(self, request: ChatRequest):
        # 1. 과거 이력 조회
        chat_history = await self.get_health_history(request.patient_id)
        print(f">>> chat_history: \n{chat_history} \n<<<")
        medi_history = await self.get_medi_history(request.patient_id)
        print(f">>> medi_history: \n{medi_history} \n<<<")
        chat_hist_str = "\n".join([f"- {h['created_at'].date()}: {h['user_question']}" for h in chat_history])
        print(f">>> chat_hist_str: \n{chat_hist_str} \n<<<")
        medi_hist_str = "\n".join(
            [f"- {h['created_at'].date()}: {h['disease_code']}: {h['medications']}" for h in medi_history]
        )
        print(f">>> medi_hist_str: \n{medi_hist_str} \n<<<")

        # 2. 사용자 요청 본문
        user_content = f"""
        - 사용자 질문: {request.user_question}
        """
        print(f">>> user_content: {user_content} \n<<<")

        # 3. 시스템 프롬프트
        system_prompt = f"""{COMMON_SYSTEM_PROMPT}\n
        당신은 환자의 일상 건강을 관리하는 '전문의 겸 건강 코치'입니다.
        사용자의 질문에 성실히 답변하며 기존의 복약이력과 질문 내역을 참고해 답변을 작성하세요.
        - 최근 질문 내역: {chat_hist_str if chat_hist_str else "없음"}
        - 과거 복약 이력: {medi_hist_str if medi_hist_str else "없음"}
        사용자가 식단, 운동, 생활 등의 질문을 하는 경우 아래 내용을 기준으로 답변하세요.
        1. [답변]: 사용자의 궁금증에 대한 의학적 근거 기반의 상세 답변
        2. [식단 추천]: 해당 건강 이슈에 도움을 주는 음식과 피해야 할 음식
        3. [운동/생활]: 실천 가능한 구체적인 운동 방법과 수면/스트레스 관리 팁.
        4. 환자에게 동기를 부여하는 따뜻하고 권위 있는 말투를 유지하세요."""
        print(f">>> system_prompt: \n{system_prompt} \n<<<")

        # 5. AI 분석
        ai_result = await self.ai.get_advice(system_prompt, request.user_question)

        # 5. 건강상담이력 테이블에 저장
        await HealthChat.create(
            patient_id=request.patient_id, user_question=request.user_question, advice=ai_result.get("chat_answer", "")
        )

        return ai_result
