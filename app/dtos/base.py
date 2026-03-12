from pydantic import BaseModel, ConfigDict


class BaseSerializerModel(BaseModel):
    """
    ORM 모델 직렬화를 위한 베이스 Pydantic 모델.

    ``from_attributes=True``로 Tortoise ORM 인스턴스를 직접 직렬화 가능.
    """

    model_config = ConfigDict(from_attributes=True)
