"""
건강관리 라우터: 체크리스트 이력 조회, 일자별 상세, 로그 상태 업데이트
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.health import (
    HealthDayDetailResponse,
    HealthHistoryListResponse,
    HealthLogUpdateRequest,
    HealthLogUpdateResponse,
)
from app.models.users import User
from app.services.health import HealthService

health_router = APIRouter(prefix="/health", tags=["health"])


@health_router.get("/history", response_model=HealthHistoryListResponse, status_code=status.HTTP_200_OK)
async def get_health_history(
    user: Annotated[User, Depends(get_request_user)],
    health_service: Annotated[HealthService, Depends(HealthService)],
    date_from: Annotated[str | None, Query(alias="from")] = None,
    date_to: Annotated[str | None, Query(alias="to")] = None,
) -> Response:
    """
    건강관리 체크리스트 이력 목록 조회.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        health_service (HealthService): 건강관리 서비스 의존성.
        date_from (str | None): 조회 시작일 (YYYY-MM-DD). 없으면 최근 30일.
        date_to (str | None): 조회 종료일 (YYYY-MM-DD).

    Returns:
        Response: HealthHistoryListResponse 직렬화 데이터.
    """
    result = await health_service.list_history(user_id=user.id, date_from=date_from, date_to=date_to)
    return Response(HealthHistoryListResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)


@health_router.get("/history/{date}", response_model=HealthDayDetailResponse, status_code=status.HTTP_200_OK)
async def get_health_day_detail(
    user: Annotated[User, Depends(get_request_user)],
    health_service: Annotated[HealthService, Depends(HealthService)],
    date: Annotated[str, Path(..., description="YYYY-MM-DD")],
) -> Response:
    """
    특정 일자 건강관리 체크리스트 상세 조회.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        health_service (HealthService): 건강관리 서비스 의존성.
        date (str): 조회할 날짜 (YYYY-MM-DD).

    Returns:
        Response: HealthDayDetailResponse 직렬화 데이터.

    Raises:
        HTTPException: 날짜 형식 오류 시 400.
    """
    result = await health_service.get_day_detail(user_id=user.id, date=date)
    return Response(HealthDayDetailResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)


@health_router.patch("/logs/{log_id}", response_model=HealthLogUpdateResponse, status_code=status.HTTP_200_OK)
async def update_health_log(
    user: Annotated[User, Depends(get_request_user)],
    health_service: Annotated[HealthService, Depends(HealthService)],
    log_id: Annotated[int, Path(..., ge=1)],
    request: HealthLogUpdateRequest,
) -> Response:
    """
    건강관리 체크리스트 로그 상태 업데이트 (done / skipped).

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        health_service (HealthService): 건강관리 서비스 의존성.
        log_id (int): 업데이트할 체크리스트 로그 ID.
        request (HealthLogUpdateRequest): 변경할 상태값.

    Returns:
        Response: HealthLogUpdateResponse (업데이트 여부 + 해당 일자 상세).

    Raises:
        HTTPException: 로그 미존재 또는 권한 없음 시 404.
    """
    result = await health_service.update_log(user_id=user.id, log_id=log_id, data=request)
    return Response(HealthLogUpdateResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)
