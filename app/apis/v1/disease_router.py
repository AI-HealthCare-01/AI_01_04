"""상병코드 검색 라우터."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import ORJSONResponse as Response

from app.dependencies.security import get_request_user
from app.models.diseases import DiseaseCodeMapping
from app.models.users import User

disease_router = APIRouter(prefix="/diseases", tags=["diseases"])


@disease_router.get("/search", status_code=status.HTTP_200_OK)
async def search_diseases(
    user: Annotated[User, Depends(get_request_user)],
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> Response:
    """상병코드 또는 질병명으로 검색."""
    try:
        keyword = q.strip()
        results = await DiseaseCodeMapping.filter(name__icontains=keyword).limit(limit)
        if not results:
            results = await DiseaseCodeMapping.filter(code__istartswith=keyword.upper()).limit(limit)
        return Response(
            [{"code": r.code, "name": r.name, "display": f"{r.code} {r.name}"} for r in results],
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="질병 검색 중 오류가 발생했습니다.") from None
