"""
복약 라우터: 복약 이력 조회, 일자별 상세, 로그 상태 업데이트
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.medication import (
    MedicationDayDetailResponse,
    MedicationHistoryListResponse,
    MedicationLogUpdateRequest,
    MedicationLogUpdateResponse,
)
from app.models.users import User
from app.services.medication import MedicationService

medication_router = APIRouter(prefix="/medications", tags=["medications"])

SortOrder = Literal["asc", "desc"]


@medication_router.get(
    "/history",
    response_model=MedicationHistoryListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_medication_history(
    user: Annotated[User, Depends(get_request_user)],
    medication_service: Annotated[MedicationService, Depends(MedicationService)],
    date_from: Annotated[str | None, Query(alias="from", description="YYYY-MM-DD")] = None,
    date_to: Annotated[str | None, Query(alias="to", description="YYYY-MM-DD")] = None,
    page: Annotated[int, Query(ge=1, description="1-based page")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="page size")] = 14,
    sort: Annotated[SortOrder, Query(description="date sort order: asc|desc")] = "desc",
) -> Response:
    """
    복약 이력 목록 조회 (일자별 달성률 요약).

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        medication_service (MedicationService): 복약 서비스 의존성.
        date_from (str | None): 조회 시작일 (YYYY-MM-DD). 없으면 최근 30일.
        date_to (str | None): 조회 종료일 (YYYY-MM-DD).
        page (int): 페이지 번호 (1-based).
        size (int): 페이지 크기 (1~100).
        sort (SortOrder): 날짜 정렬 방향 (``asc`` | ``desc``).

    Returns:
        Response: MedicationHistoryListResponse 직렬화 데이터.
    """
    result = await medication_service.list_history(
        user_id=user.id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
        sort=sort,
    )
    return Response(MedicationHistoryListResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)


@medication_router.get(
    "/history/{date}",
    response_model=MedicationDayDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_medication_day_detail(
    user: Annotated[User, Depends(get_request_user)],
    medication_service: Annotated[MedicationService, Depends(MedicationService)],
    date: Annotated[str, Path(..., description="YYYY-MM-DD")],
) -> Response:
    """
    특정 일자 복약 체크리스트 상세 조회.

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        medication_service (MedicationService): 복약 서비스 의존성.
        date (str): 조회할 날짜 (YYYY-MM-DD).

    Returns:
        Response: MedicationDayDetailResponse 직렬화 데이터.

    Raises:
        HTTPException: 날짜 형식 오류 시 400.
    """
    result = await medication_service.get_day_detail(user_id=user.id, date=date)
    return Response(MedicationDayDetailResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)


@medication_router.patch(
    "/logs/{log_id}",
    response_model=MedicationLogUpdateResponse,
    status_code=status.HTTP_200_OK,
)
async def update_medication_log(
    user: Annotated[User, Depends(get_request_user)],
    medication_service: Annotated[MedicationService, Depends(MedicationService)],
    log_id: Annotated[int, Path(..., ge=1)],
    request: MedicationLogUpdateRequest,
) -> Response:
    """
    복약 로그 상태 업데이트 (taken / skipped / delayed).

    Args:
        user (User): JWT 인증으로 확인된 현재 사용자.
        medication_service (MedicationService): 복약 서비스 의존성.
        log_id (int): 업데이트할 복약 로그 ID.
        request (MedicationLogUpdateRequest): 변경할 상태값.

    Returns:
        Response: MedicationLogUpdateResponse (업데이트 여부 + 해당 일자 상세).

    Raises:
        HTTPException: 로그 미존재 또는 권한 없음 시 404.
    """
    result = await medication_service.update_log(user_id=user.id, log_id=log_id, data=request)
    return Response(MedicationLogUpdateResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)
