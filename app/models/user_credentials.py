"""
사용자 인증 정보 모델 (ERD 기반)

📚 학습 포인트:
- OneToOneField: 1:1 관계 (한 사용자당 하나의 credential)
- related_name: 역참조 시 사용 (user.credentials 로 접근)
- 비밀번호를 users 테이블과 분리하는 이유:
  1. OAuth 사용자는 비밀번호가 없을 수 있음
  2. 비밀번호 변경 이력 관리 용이
  3. 보안상 민감 정보 분리
"""
from tortoise import fields, models


class UserCredential(models.Model):
    """
    사용자 비밀번호 정보 (ERD: user_credentials)

    users 테이블과 1:1 관계
    """

    user = fields.OneToOneField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="credential",
        pk=True,  # user_id가 PK (1:1이므로)
    )
    password_hash = fields.CharField(max_length=255)
    password_updated_at = fields.DatetimeField(null=True)

    class Meta:
        table = "user_credentials"
