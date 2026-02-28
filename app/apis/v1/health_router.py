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
    result = await health_service.list_history(user_id=user.id, date_from=date_from, date_to=date_to)
    return Response(HealthHistoryListResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)


@health_router.get("/history/{date}", response_model=HealthDayDetailResponse, status_code=status.HTTP_200_OK)
async def get_health_day_detail(
    user: Annotated[User, Depends(get_request_user)],
    health_service: Annotated[HealthService, Depends(HealthService)],
    date: Annotated[str, Path(..., description="YYYY-MM-DD")],
) -> Response:
    result = await health_service.get_day_detail(user_id=user.id, date=date)
    return Response(HealthDayDetailResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)


@health_router.patch("/logs/{log_id}", response_model=HealthLogUpdateResponse, status_code=status.HTTP_200_OK)
async def update_health_log(
    user: Annotated[User, Depends(get_request_user)],
    health_service: Annotated[HealthService, Depends(HealthService)],
    log_id: Annotated[int, Path(..., ge=1)],
    request: HealthLogUpdateRequest,
) -> Response:
    result = await health_service.update_log(user_id=user.id, log_id=log_id, data=request)
    return Response(HealthLogUpdateResponse.model_validate(result).model_dump(), status_code=status.HTTP_200_OK)
