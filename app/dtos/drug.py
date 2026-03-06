from pydantic import BaseModel


class DrugSearchItemResponse(BaseModel):
    id: int
    name: str
    manufacturer: str | None = None
