from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.recommendations import (
    RecommendationResponse,
    RecommendationSaveResponse,
    RecommendationUpdateRequest,
    ScanRecommendationListResponse,
)
from app.models.users import User
from app.services.recommendations import RecommendationService

recommendation_router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@recommendation_router.get(
    "",
    response_model=list[RecommendationResponse],
    status_code=status.HTTP_200_OK,
)
async def list_recommendations(
    user: Annotated[User, Depends(get_request_user)],
    recommendation_service: Annotated[RecommendationService, Depends(RecommendationService)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Response:
    """
    사용자의 추천 목록 조회
    """
    result = await recommendation_service.list_by_user(user_id=user.id, limit=limit, offset=offset)
    return Response(result, status_code=status.HTTP_200_OK)


@recommendation_router.get(
    "/active",
    response_model=list[RecommendationResponse],
    status_code=status.HTTP_200_OK,
)
async def list_active_recommendations(
    user: Annotated[User, Depends(get_request_user)],
    recommendation_service: Annotated[RecommendationService, Depends(RecommendationService)],
) -> Response:
    """
    현재 활성화된 추천 목록 조회
    """
    result = await recommendation_service.list_active(user_id=user.id)
    return Response(result, status_code=status.HTTP_200_OK)


@recommendation_router.get(
    "/scans/{scan_id}",
    response_model=ScanRecommendationListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_recommendations_for_scan(
    user: Annotated[User, Depends(get_request_user)],
    recommendation_service: Annotated[RecommendationService, Depends(RecommendationService)],
    scan_id: Annotated[int, Path(..., ge=1)],
) -> Response:
    """
    특정 scan(OCR 결과) 기반 건강관리 추천 리스트 조회/생성
    - 진단명 기반 가이드
    - 약물 기반 주의사항/생활관리
    """
    result = await recommendation_service.get_for_scan(user_id=user.id, scan_id=scan_id)
    return Response(
        ScanRecommendationListResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@recommendation_router.patch(
    "/{recommendation_id}",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
)
async def update_recommendation(
    user: Annotated[User, Depends(get_request_user)],
    recommendation_service: Annotated[RecommendationService, Depends(RecommendationService)],
    recommendation_id: Annotated[int, Path(..., ge=1)],
    data: RecommendationUpdateRequest,
) -> Response:
    """
    추천 항목 수정 (운동 빈도/양 등 사용자 편집)
    """
    result = await recommendation_service.update(user_id=user.id, recommendation_id=recommendation_id, data=data)
    return Response(
        RecommendationResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@recommendation_router.delete(
    "/{recommendation_id}",
    status_code=status.HTTP_200_OK,
)
async def delete_recommendation(
    user: Annotated[User, Depends(get_request_user)],
    recommendation_service: Annotated[RecommendationService, Depends(RecommendationService)],
    recommendation_id: Annotated[int, Path(..., ge=1)],
) -> Response:
    """
    추천 항목 삭제
    """
    await recommendation_service.delete(user_id=user.id, recommendation_id=recommendation_id)
    return Response({"deleted": True}, status_code=status.HTTP_200_OK)


@recommendation_router.post(
    "/scans/{scan_id}/save",
    response_model=RecommendationSaveResponse,
    status_code=status.HTTP_200_OK,
)
async def save_recommendations_for_scan(
    user: Annotated[User, Depends(get_request_user)],
    recommendation_service: Annotated[RecommendationService, Depends(RecommendationService)],
    scan_id: Annotated[int, Path(..., ge=1)],
) -> Response:
    """
    scan 기반 추천들을 '확정 저장' 처리 (사용자 계정에 활성 추천으로 반영)
    """
    result = await recommendation_service.save_for_scan(user_id=user.id, scan_id=scan_id)
    return Response(
        RecommendationSaveResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@recommendation_router.post(
    "/{recommendation_id}/feedback",
    status_code=status.HTTP_200_OK,
)
async def add_recommendation_feedback(
    user: Annotated[User, Depends(get_request_user)],
    recommendation_service: Annotated[RecommendationService, Depends(RecommendationService)],
    recommendation_id: Annotated[int, Path(..., ge=1)],
    feedback_type: Annotated[str, Query(..., pattern="^(like|dislike|click)$")],
) -> Response:
    """
    추천에 대한 피드백 추가 (like, dislike, click)
    """
    result = await recommendation_service.add_feedback(
        user_id=user.id, recommendation_id=recommendation_id, feedback_type=feedback_type
    )
    return Response(result, status_code=status.HTTP_200_OK)
