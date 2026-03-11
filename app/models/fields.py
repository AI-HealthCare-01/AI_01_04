from __future__ import annotations

from tortoise.fields import TextField


class VectorField(TextField):
    SQL_TYPE = "vector(1536)"

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
        return {"": "vector(1536)", "postgres": "vector(1536)"}