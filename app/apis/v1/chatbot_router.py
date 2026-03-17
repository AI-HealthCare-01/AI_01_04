from __future__ import annotations

import logging

from fastapi import APIRouter

from app.dtos.chat import (
    ChatRequest,
    ChatResponse,
    DeactivateRequest,
    DeactivateResponse,
    UserContextResponse,
)
from app.services.chat_base_service import ChatBaseService as BaseService
from app.services.chat_context_service import ChatContextService
from app.services.chat_health_service import ChatHealthService
from app.services.chat_medi_service import ChatMediService

logger = logging.getLogger(__name__)

chatbot_router = APIRouter(prefix="/chatbot", tags=["Medical API"])


@chatbot_router.get("/check-patient/{patient_id}")
async def check_patient(patient_id: str):
    service = BaseService()
    exists = await service.check_user_exists(patient_id)
    return {"exists": exists}


@chatbot_router.get("/history/{patient_id}")
async def get_history(patient_id: str):
    service = BaseService()
    return await service.get_medi_history(patient_id)


@chatbot_router.get("/context/{user_id}", response_model=UserContextResponse)
async def get_user_context(user_id: int):
    """사용자의 질병, active 약품, 스캔 이력을 조회한다."""
    service = ChatContextService()
    return await service.get_user_context(user_id)


@chatbot_router.post("/deactivate", response_model=DeactivateResponse)
async def deactivate_medication(request: DeactivateRequest):
    """처방전(약품)을 비활성화한다."""
    # TODO: JWT 인증에서 user_id 추출. 현재는 임시로 prescription에서 user 확인
    from app.models.prescriptions import Prescription

    rx = await Prescription.get_or_none(id=request.prescription_id)
    if not rx:
        return DeactivateResponse(success=False, message="처방전을 찾을 수 없습니다.")

    await rx.fetch_related("user")
    service = ChatContextService()
    ok = await service.deactivate_prescription(rx.user.id, request.prescription_id)
    if ok:
        return DeactivateResponse(success=True, message="약품이 비활성화되었습니다.")
    return DeactivateResponse(success=False, message="비활성화에 실패했습니다.")


@chatbot_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    logger.debug("chat_endpoint: %s", request)
    if request.mode == "medication":
        medi_service = ChatMediService()
        return await medi_service.process_medical_chat(request)
    else:
        health_service = ChatHealthService()
        return await health_service.process_health_chat(request)
