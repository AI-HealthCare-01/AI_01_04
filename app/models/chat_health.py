from tortoise import fields, models


class HealthChat(models.Model):
    id = fields.IntField(pk=True)
    patient_id = fields.CharField(max_length=50, index=True)
    user_question = fields.TextField()
    advice = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "health_chat"
