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
    result = await medication_service.update_log(user_id=user.id, log_id=log_id, data=request)
    return Response(MedicationLogUpdateResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)
