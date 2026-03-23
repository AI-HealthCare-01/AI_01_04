from __future__ import annotations

import logging

from app.repositories.disease_repository import DiseaseRepository

from ..dtos.chat import ChatRequest
from ..models.chat_medication import MediChat
from ..utils.constants import COMMON_SYSTEM_PROMPT, COMMON_USER_PROMPT
from .chat_base_service import ChatBaseService as BaseService
from .chat_context_service import ChatContextService
from .chat_openai_service import ChatOpenaiService as OpenAI

logger = logging.getLogger(__name__)


class ChatMediService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self.ai = OpenAI()
        self.disease_repo = DiseaseRepository()
        self.context_service = ChatContextService()

    async def process_medical_chat(self, request: ChatRequest):
        user_id = int(request.patient_id)

        # 1. 세션 확보
        if request.session_id:
            session = await self.chatbot_repo.get_session(user_id, request.session_id)
            if not session:
                session = await self.chatbot_repo.create_session(user_id, "medication")
        else:
            session = await self.chatbot_repo.get_or_create_active_session(user_id, "medication")

        # 2. 사용자 메시지 저장
        user_question = (request.user_question or "").strip()
        if user_question:
            await self.chatbot_repo.add_message(session.id, "user", user_question)

        # 3. 세션 내 대화 맥락 조회
        messages = await self.chatbot_repo.get_messages(session.id)
        conversation_str = self.build_conversation_context(messages)

        # 4. 이전 세션 요약
        prev_summary = await self.chatbot_repo.get_latest_summary(user_id, "medication")

        # 5. 사용자 컨텍스트 자동 조회
        context_str = ""
        disease_name = request.disease_code or ""
        med_names: list[str] = request.medications or []

        if request.use_context:
            ctx = await self.context_service.get_user_context(user_id)
            context_str = self.context_service.build_context_prompt(ctx)

            if ctx["diseases"] and not request.disease_code:
                disease_name = ", ".join(d["name"] for d in ctx["diseases"])
            if ctx["medications"] and not request.medications:
                med_names = [m["drug_name"] for m in ctx["medications"]]

        # 6. 질병코드 → anchor 코드 + 가이드라인 조회
        anchor_code, resolved_name, guideline_texts = await self.disease_repo.resolve_disease_info(
            request.disease_code or disease_name
        )
        disease_name = resolved_name or disease_name

        # 7. 과거 복약 이력 (레거시)
        history = await self.get_medi_history(request.patient_id)
        history_str = "\n".join([f"- {h['created_at'].date()}: {h['medications']}" for h in history])

        # 8. 가이드라인 텍스트
        guideline_str = "\n".join(f"- {g}" for g in guideline_texts) if guideline_texts else ""

        # 9. 사용자 요청 본문
        user_content = f"""
        [환자 정보]
        - 질병명: {disease_name}{f" (코드: {anchor_code})" if anchor_code else ""}
        - 현재 처방약: {", ".join(med_names) if med_names else "없음"}
        - 과거 복약 이력: {history_str if history_str else "없음"}
        {f"[사용자 등록 정보]{chr(10)}{context_str}" if context_str else ""}
        {f"[이전 대화 요약]{chr(10)}{prev_summary}" if prev_summary else ""}
        {f"[현재 대화 맥락]{chr(10)}{conversation_str}" if conversation_str else ""}
        [사용자 질문]
        {user_question if user_question else "(질문 없음 — 전반적인 복약 안내를 제공하세요)"}
        {COMMON_USER_PROMPT}"""

        # 10. 시스템 프롬프트
        guideline_section = ""
        if guideline_str:
            guideline_section = f"""
        [참고 가이드라인 - 반드시 답변에 반영하세요]
        {guideline_str}"""

        system_prompt = f"""
        당신은 따뜻하고 신뢰감 있는 전문 AI 의료 파트너입니다.
        환자의 질병({disease_name})과 처방약, 과거 복약 이력을 종합적으로 분석하여 다음 규칙을 따르세요:
        - 사용자의 질문이 있으면 해당 질문에 직접적으로 답변하세요. 질문과 무관한 일반 리포트를 작성하지 마세요.
        - 이전 대화 맥락이 있으면 흐름을 이어서 답변하세요.
        - 질문이 없을 때만 아래 항목을 포함한 전반적인 복약 안내를 제공하세요:
          1. [복용법]: 성분별 최적의 복용 시간(식전/식후)과 용량, 주의사항을 설명하세요.
          2. [상호작용]: 처방약 간 또는 흔한 영양제와의 충돌 위험을 경고하세요.
          3. [부작용]: 즉시 복용을 중단해야 하는 위험 징후를 명시하세요.{guideline_section}
        {COMMON_SYSTEM_PROMPT}"""

        # 11. AI 분석
        ai_result = await self.ai.get_advice(system_prompt, user_content)
        logger.debug("AI 복약지도 결과: %s", ai_result)

        # 12. AI 응답을 세션 메시지로 저장
        answer = ai_result.get("chat_answer", "")
        if answer:
            await self.chatbot_repo.add_message(session.id, "assistant", answer)

        # 13. 레거시 테이블에도 저장 (하위호환)
        saved_disease = request.disease_code or disease_name or anchor_code or ""
        await MediChat.create(
            patient_id=request.patient_id,
            disease_code=saved_disease,
            medications=", ".join(med_names),
            advice=answer,
        )

        ai_result["session_id"] = session.id
        return ai_result
