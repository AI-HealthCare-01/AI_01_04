from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies.security import get_request_user
from app.dtos.chat import (
    ChatRequest,
    ChatResponse,
    DeactivateRequest,
    DeactivateResponse,
    UserContextResponse,
)
from app.models.chat_health import HealthChat
from app.models.chat_medication import MediChat
from app.models.users import User
from app.services.chat_base_service import ChatBaseService as BaseService
from app.services.chat_context_service import ChatContextService
from app.services.chat_health_service import ChatHealthService
from app.services.chat_medi_service import ChatMediService
from app.services.chat_openai_service import ChatOpenaiService

logger = logging.getLogger(__name__)

chatbot_router = APIRouter(prefix="/chatbot", tags=["Medical API"])


@chatbot_router.get("/check-patient/{patient_id}")
async def check_patient(
    patient_id: str,
    user: Annotated[User, Depends(get_request_user)],
):
    service = BaseService()
    exists = await service.check_user_exists(patient_id)
    return {"exists": exists}


@chatbot_router.get("/history/{patient_id}")
async def get_history(
    patient_id: str,
    user: Annotated[User, Depends(get_request_user)],
):
    service = BaseService()
    return await service.get_medi_history(patient_id)


@chatbot_router.get("/health-history/{patient_id}")
async def get_health_history(
    patient_id: str,
    user: Annotated[User, Depends(get_request_user)],
):
    service = BaseService()
    return await service.get_health_history(patient_id)


@chatbot_router.get("/context/{user_id}", response_model=UserContextResponse)
async def get_user_context(
    user_id: int,
    user: Annotated[User, Depends(get_request_user)],
):
    """사용자의 질병, active 약품, 스캔 이력을 조회한다."""
    if user.id != user_id and not user.is_admin:  # 접속 유저 외 다른 유저 접근 차단 및 관리자 접근가능
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    service = ChatContextService()
    return await service.get_user_context(user_id)


@chatbot_router.post("/deactivate", response_model=DeactivateResponse)
async def deactivate_medication(
    request: DeactivateRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    """처방전(약품)을 비활성화한다."""
    from app.models.prescriptions import Prescription

    rx = await Prescription.get_or_none(id=request.prescription_id)
    if not rx:
        return DeactivateResponse(success=False, message="처방전을 찾을 수 없습니다.")

    await rx.fetch_related("user")
    if rx.user.id != user.id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    service = ChatContextService()
    ok = await service.deactivate_prescription(user.id, request.prescription_id)
    if ok:
        return DeactivateResponse(success=True, message="약품이 비활성화되었습니다.")
    return DeactivateResponse(success=False, message="비활성화에 실패했습니다.")


@chatbot_router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    logger.debug("chat_endpoint: %s", request)
    request.patient_id = str(user.id)

    if request.mode == "medication":
        medi_service = ChatMediService()
        return await medi_service.process_medical_chat(request)

    health_service = ChatHealthService()
    return await health_service.process_health_chat(request)


@chatbot_router.post("/chat/stream")
async def chat_stream_endpoint(
    request: ChatRequest,
    user: Annotated[User, Depends(get_request_user)],
):
    request.patient_id = str(user.id)
    ai = ChatOpenaiService()

    try:
        if request.mode == "medication":
            medi_service = ChatMediService()
            system_prompt, user_content, session_id = await medi_service.prepare_medical_stream(request)
        else:
            health_service = ChatHealthService()
            system_prompt, user_content, session_id = await health_service.prepare_health_stream(request)
    except Exception:
        logger.exception("chat_stream prepare failed")
        raise HTTPException(status_code=500, detail="상담 준비 중 오류가 발생했습니다.") from None

    service = medi_service if request.mode == "medication" else health_service  # type: ignore[possibly-undefined]

    async def event_generator():
        full_answer = []
        async for chunk in ai.stream_advice(system_prompt, user_content):
            full_answer.append(chunk)
            yield f"data: {json.dumps({'token': chunk}, ensure_ascii=False)}\n\n"

        answer = "".join(full_answer)
        if answer:
            await service.chatbot_repo.add_message(session_id, "assistant", answer)

        if request.mode == "medication":
            await MediChat.create(
                patient_id=request.patient_id,
                disease_code=request.disease_code or "",
                medications=", ".join(request.medications or []),
                advice=answer,
            )
        else:
            await HealthChat.create(
                patient_id=request.patient_id,
                user_question=request.user_question,
                advice=answer,
            )

        await service.maybe_summarize_and_rotate(session_id, int(request.patient_id), request.mode or "medication")
        yield f"data: {json.dumps({'done': True, 'session_id': str(session_id)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
