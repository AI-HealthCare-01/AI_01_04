from __future__ import annotations

import logging

from app.repositories.disease_repository import DiseaseRepository

from ..models.chat_health import HealthChat
from ..dtos.chat import ChatRequest
from ..utils.constants import COMMON_SYSTEM_PROMPT
from .chat_base_service import ChatBaseService as BaseService
from .chat_openai_service import ChatOpenaiService as OpenAI

logger = logging.getLogger(__name__)


class ChatHealthService(BaseService):
    def __init__(self) -> None:
        super().__init__()
        self.ai = OpenAI()
        self.disease_repo = DiseaseRepository()

    async def _collect_guidelines_from_history(self, medi_history: list[dict]) -> str:
        """복약 이력의 질병코드들에서 가이드라인을 수집하여 텍스트로 반환한다."""
        seen_codes: set[str] = set()
        lines: list[str] = []

        for h in medi_history:
            code = h.get("disease_code") or ""
            if not code.strip() or code.strip() in seen_codes:
                continue
            seen_codes.add(code.strip())

            _anchor, name, guideline_texts = await self.disease_repo.resolve_disease_info(code.strip())
            if guideline_texts:
                label = name or code.strip()
                lines.append(f"[{label}]")
                lines.extend(f"  - {g}" for g in guideline_texts)

        return "\n".join(lines)

    async def process_health_chat(self, request: ChatRequest):
        user_id = int(request.patient_id)

        # 1. 과거 이력 조회
        chat_history = await self.get_health_history(request.patient_id)
        medi_history = await self.get_medi_history(request.patient_id)
        chat_hist_str = "\n".join([f"- {h['created_at'].date()}: {h['user_question']}" for h in chat_history])
        medi_hist_str = "\n".join(
            [f"- {h['created_at'].date()}: {h['disease_code']}: {h['medications']}" for h in medi_history]
        )

        # 2. 복약 이력 기반 가이드라인 수집
        guideline_str = await self._collect_guidelines_from_history(medi_history)

        # 3. 사용자 요청 본문
        user_content = f"""
        - 사용자 질문: {request.user_question}
        """

        # 4. 시스템 프롬프트
        guideline_section = ""
        if guideline_str:
            guideline_section = f"""
        [환자의 기존 질환 관련 가이드라인 - 답변 시 참고하세요]
        {guideline_str}"""

        system_prompt = f"""{COMMON_SYSTEM_PROMPT}\n
        당신은 환자의 일상 건강을 관리하는 '전문의 겸 건강 코치'입니다.
        사용자의 질문에 성실히 답변하며 기존의 복약이력과 질문 내역을 참고해 답변을 작성하세요.
        - 최근 질문 내역: {chat_hist_str if chat_hist_str else "없음"}
        - 과거 복약 이력: {medi_hist_str if medi_hist_str else "없음"}{guideline_section}
        사용자가 식단, 운동, 생활 등의 질문을 하는 경우 아래 내용을 기준으로 답변하세요.
        1. [답변]: 사용자의 궁금증에 대한 의학적 근거 기반의 상세 답변
        2. [식단 추천]: 해당 건강 이슈에 도움을 주는 음식과 피해야 할 음식
        3. [운동/생활]: 실천 가능한 구체적인 운동 방법과 수면/스트레스 관리 팁.
        4. 환자에게 동기를 부여하는 따뜻하고 권위 있는 말투를 유지하세요."""

        # 5. AI 분석
        ai_result = await self.ai.get_advice(system_prompt, user_content)
        logger.debug("AI 건강상담 결과: %s", ai_result)

        # 6. 건강상담이력 테이블에 저장
        await HealthChat.create(
            patient_id=request.patient_id, user_question=request.user_question, advice=ai_result.get("chat_answer", "")
        )

        return ai_result
