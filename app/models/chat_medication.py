from tortoise import fields, models


class MediChat(models.Model):
    id = fields.IntField(pk=True)
    patient_id = fields.CharField(max_length=50, index=True)
    disease_code = fields.CharField(max_length=20, null=True)
    medications = fields.TextField(null=True)
    advice = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "medi_chat"
