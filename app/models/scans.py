from tortoise import fields, models
from tortoise.fields.relational import ForeignKeyRelation

from app.models.users import User


class Scan(models.Model):
    id = fields.IntField(pk=True)
    user: ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="scans",
    )

    status = fields.CharField(max_length=30, default="uploaded")
    analyzed_at = fields.DatetimeField(null=True)

    document_date = fields.CharField(max_length=10, null=True)
    diagnosis = fields.TextField(null=True)
    drugs: list[str] = fields.JSONField(default=list)  # type: ignore[assignment]

    raw_text = fields.TextField(null=True)
    ocr_raw: dict = fields.JSONField(null=True)  # type: ignore[assignment]

    file_path = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "scans"
        indexes = (("user_id", "id"), ("user_id", "created_at"))
