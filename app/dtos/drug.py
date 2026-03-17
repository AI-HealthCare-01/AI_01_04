from pydantic import BaseModel


class DrugSearchItemResponse(BaseModel):
    """약품 검색 결과 단일 항목 응답 스키마."""

    id: int
    name: str
    manufacturer: str | None = None
