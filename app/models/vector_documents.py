"""
벡터 임베딩 문서 모델 (ERD 기반)

📚 학습 포인트:
- RAG/검색용: 텍스트를 벡터로 변환해 유사도 검색
- reference_type + reference_id: 어떤 엔티티의 내용인지 (다형성 참조)
- MySQL에는 vector 타입이 없어 JSON으로 저장 (1536차원 = OpenAI embedding)
"""
from tortoise import fields, models


class VectorDocument(models.Model):
    """
    벡터 임베딩 문서 (ERD: vector_documents)

    - reference_type: 'disease_guideline', 'chatbot_summary' 등
    - reference_id: 해당 테이블의 id
    - embedding: 1536차원 벡터 (OpenAI text-embedding-3-small 등)
    """

    id = fields.IntField(pk=True)
    reference_type = fields.CharField(max_length=100)
    reference_id = fields.IntField()
    content = fields.TextField()
    embedding = fields.JSONField()  # [0.1, -0.2, ...] 1536개 float
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "vector_documents"
