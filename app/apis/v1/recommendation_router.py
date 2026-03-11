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
    사용자의 추천 목록을 조회한다.

    Args:
        user (User):
            인증된 사용자 객체
        recommendation_service (RecommendationService):
            추천 서비스 객체
        limit (int):
            조회할 최대 추천 개수
        offset (int):
            조회 시작 위치

    Returns:
        Response:
            추천 목록 응답
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
    현재 활성화된 추천 목록을 조회한다.

    Args:
        user (User):
            인증된 사용자 객체
        recommendation_service (RecommendationService):
            추천 서비스 객체

    Returns:
        Response:
            활성 추천 목록 응답
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
    특정 scan 결과 기반 추천 목록을 조회하거나 생성한다.

    처리 흐름:
    1. scan_id에 해당하는 스캔 결과를 조회한다.
    2. 이미 생성된 추천이 있으면 재사용한다.
    3. 없으면 진단명/질병코드/약물 정보를 바탕으로 추천을 생성한다.

    Args:
        user (User):
            인증된 사용자 객체
        recommendation_service (RecommendationService):
            추천 서비스 객체
        scan_id (int):
            스캔 ID

    Returns:
        Response:
            scan 기반 추천 목록 응답
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
    추천 항목 내용을 수정하거나 선택 여부를 갱신한다.

    Args:
        user (User):
            인증된 사용자 객체
        recommendation_service (RecommendationService):
            추천 서비스 객체
        recommendation_id (int):
            추천 ID
        data (RecommendationUpdateRequest):
            수정 요청 데이터

    Returns:
        Response:
            수정된 추천 항목 응답
    """
    result = await recommendation_service.update(
        user_id=user.id,
        recommendation_id=recommendation_id,
        data=data,
    )
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
    추천 항목을 삭제 상태(철회 상태)로 변경한다.

    실제 DB 레코드를 물리 삭제하지 않고,
    서비스 레이어에서 status 값을 변경하는 방식으로 처리한다.

    Args:
        user (User):
            인증된 사용자 객체
        recommendation_service (RecommendationService):
            추천 서비스 객체
        recommendation_id (int):
            추천 ID

    Returns:
        Response:
            삭제 처리 결과 응답
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
    특정 scan 기반 추천을 사용자 활성 추천으로 저장한다.

    처리 규칙:
    - 사용자가 선택한 추천(is_selected=True)이 있으면 그것만 저장한다.
    - 선택한 추천이 없으면 해당 scan의 전체 추천을 저장한다.

    Args:
        user (User):
            인증된 사용자 객체
        recommendation_service (RecommendationService):
            추천 서비스 객체
        scan_id (int):
            스캔 ID

    Returns:
        Response:
            저장 결과 응답
    """
    result = await recommendation_service.save_for_scan(user_id=user.id, scan_id=scan_id)
    return Response(
        RecommendationSaveResponse.model_validate(result).model_dump(),
        status_code=status.HTTP_200_OK,
    )


@recommendation_router.post(
    "/{recommendation_id}/feedback",
    status_code=status.HTTP_201_CREATED,
)
async def add_recommendation_feedback(
    user: Annotated[User, Depends(get_request_user)],
    recommendation_service: Annotated[RecommendationService, Depends(RecommendationService)],
    recommendation_id: Annotated[int, Path(..., ge=1)],
    feedback_type: Annotated[str, Query(..., pattern="^(like|dislike|click)$")],
) -> Response:
    """
    추천 항목에 대한 피드백을 저장한다.

    허용되는 피드백 값:
    - like
    - dislike
    - click

    Args:
        user (User):
            인증된 사용자 객체
        recommendation_service (RecommendationService):
            추천 서비스 객체
        recommendation_id (int):
            추천 ID
        feedback_type (str):
            피드백 유형

    Returns:
        Response:
            저장된 피드백 응답
    """
    result = await recommendation_service.add_feedback(
        user_id=user.id,
        recommendation_id=recommendation_id,
        feedback_type=feedback_type,
    )
    return Response(result, status_code=status.HTTP_201_CREATED)
