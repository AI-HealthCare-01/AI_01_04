from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.dtos.drug import DrugSearchItemResponse
from app.models.users import User
from app.services.drugs import DrugService

drug_router = APIRouter(prefix="/drugs", tags=["drugs"])


@drug_router.get(
    "/search",
    response_model=list[DrugSearchItemResponse],
    status_code=status.HTTP_200_OK,
)
async def search_drugs(
    user: Annotated[User, Depends(get_request_user)],
    drug_service: Annotated[DrugService, Depends(DrugService)],
    q: Annotated[str, Query(min_length=1, max_length=100, description="약품명 검색어")],
    limit: Annotated[int, Query(ge=1, le=50, description="최대 반환 개수")] = 20,
) -> Response:
    result = await drug_service.search(keyword=q, limit=limit)
    return Response(result, status_code=status.HTTP_200_OK)
