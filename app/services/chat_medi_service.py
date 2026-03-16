from __future__ import annotations

import logging

from ..models.chat_medication import MediChat
from ..schemas.chat import ChatRequest
from ..utils.constants import COMMON_SYSTEM_PROMPT, COMMON_USER_PROMPT
from .chat_base_service import ChatBaseService as BaseService
from .chat_openai_service import ChatOpenaiService as OpenAI

logger = logging.getLogger(__name__)


class ChatMediService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self.ai = OpenAI()

    async def process_medical_chat(self, request: ChatRequest):
        disease_name = request.disease_code

        # 2. 과거 복약 이력 조회
        history = await self.get_medi_history(request.patient_id)
        history_str = "\n".join([f"- {h['created_at'].date()}: {h['medications']}" for h in history])

        # 3. 사용자 요청 본문
        user_content = f"""
        [환자 정보]
        - 질병명: {disease_name}
        - 현재 처방약: {", ".join(request.medications)}
        - 과거 복약 이력: {history_str if history_str else "없음"}
        {COMMON_USER_PROMPT}"""

        # 4. 시스템 프롬프트
        system_prompt = f"""
        당신은 따뜻하고 신뢰감 있는 전문 AI 의료 파트너입니다.
        환자의 질병({disease_name})과 처방약, 과거 복약 이력을 종합적으로 분석하여 다음 규칙을 따르세요:
        1. [복용법]: 성분별 최적의 복용 시간(식전/식후)과 용량, 주의사항을 설명하세요.
        2. [상호작용]: 처방약 간 또는 흔한 영양제와의 충돌 위험을 경고하세요.
        3. [부작용]: 즉시 복용을 중단해야 하는 위험 징후를 명시하세요.
        {COMMON_SYSTEM_PROMPT}"""

        # 5. AI 분석
        ai_result = await self.ai.get_advice(system_prompt, user_content)
        logger.debug("AI 복약지도 결과: %s", ai_result)

        # 6. 복약이력 테이블에 저장
        await MediChat.create(
            patient_id=request.patient_id,
            disease_code=request.disease_code,
            medications=", ".join(request.medications),
            advice=ai_result.get("chat_answer", ""),
        )

        return ai_result
