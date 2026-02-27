from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.models.users import User
from app.services.dashboard import DashboardService
from app.dtos.dashboard import DashboardSummaryResponse

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_dashboard_summary(
    user: Annotated[User, Depends(get_request_user)],
    dashboard_service: Annotated[DashboardService, Depends(DashboardService)],
) -> Response:
    """
    사용자 대시보드 요약 정보 조회

    포함 정보:
    - 최근 처방
    - 남은 약 일수
    - 오늘 복약 여부
    - 오늘 건강관리 여부
    """

    summary = await dashboard_service.get_summary(user)

    return Response(
        DashboardSummaryResponse.model_validate(summary).model_dump(),
        status_code=status.HTTP_200_OK,
    )