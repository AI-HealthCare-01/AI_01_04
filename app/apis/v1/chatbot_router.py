from __future__ import annotations

import logging

from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_base_service import ChatBaseService as BaseService
from app.services.chat_health_service import ChatHealthService
from app.services.chat_medi_service import ChatMediService

logger = logging.getLogger(__name__)

chatbot_router = APIRouter(prefix="/chatbot", tags=["Medical API"])


""" 1. 환자 id 체크 """


@chatbot_router.get("/check-patient/{patient_id}")
async def check_patient(patient_id: str):
    service = BaseService()
    exists = await service.check_user_exists(patient_id)
    return {"exists": exists}


""" 복약이력 조회 """


@chatbot_router.get("/history/{patient_id}")
async def get_history(patient_id: str):
    service = BaseService()
    # 비동기로 이력 데이터를 가져옵니다.
    return await service.get_medi_history(patient_id)


""" 채팅 실행 """


@chatbot_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    logger.debug("chat_endpoint: %s", request)
    if request.mode == "medication":
        medi_service = ChatMediService()
        return await medi_service.process_medical_chat(request)
    else:
        health_service = ChatHealthService()
        return await health_service.process_health_chat(request)
