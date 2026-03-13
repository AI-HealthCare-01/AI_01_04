from __future__ import annotations

from tortoise.fields import TextField


class VectorField(TextField):
    """
    pgvector 확장의 vector 타입을 위한 커스텀 Tortoise ORM 필드.

    CI 환경에서는 TEXT로 동작하며, raw SQL에서 ``::vector`` 캐스팅으로 벡터 연산 처리.
    """

    SQL_TYPE = "TEXT"

    def to_db_value(self, value: list[float] | None, instance) -> str | None:
        if value is None:
            return None
        return "[" + ", ".join(str(v) for v in value) + "]"

    def to_python_value(self, value: str | list | None) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, list):
            return value
        import json

        return json.loads(value)

    def get_db_field_types(self) -> dict:
        return {"": "TEXT"}
