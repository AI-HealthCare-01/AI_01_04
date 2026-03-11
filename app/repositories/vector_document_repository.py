"""
벡터 문서 도메인 Repository

- VectorDocument: reference_type + reference_id로 다형 참조 (user_id 없음)
- user 스코프: reference가 user 소유인지는 서비스 레이어에서 검증
- 이 레포는 reference 기반 CRUD 제공, 서비스에서 user 소유 reference만 전달
"""

from __future__ import annotations

from app.models.vector_documents import VectorDocument


class VectorDocumentRepository:
    def __init__(self):
        self._model = VectorDocument

    async def get_by_id(self, doc_id: int) -> VectorDocument | None:
        return await self._model.get_or_none(id=doc_id)

    async def get_by_reference(
        self,
        reference_type: str,
        reference_id: int,
    ) -> VectorDocument | None:
        return await self._model.get_or_none(
            reference_type=reference_type,
            reference_id=reference_id,
        )

    async def list_by_reference_type_and_ids(
        self,
        reference_type: str,
        reference_ids: list[int],
    ) -> list[VectorDocument]:
        """reference_ids는 서비스에서 user 소유로 검증된 ID 목록"""
        if not reference_ids:
            return []
        return await self._model.filter(
            reference_type=reference_type,
            reference_id__in=reference_ids,
        )

    async def create(
        self,
        *,
        reference_type: str,
        reference_id: int,
        content: str,
        embedding: list[float],
    ) -> VectorDocument:
        return await self._model.create(
            reference_type=reference_type,
            reference_id=reference_id,
            content=content,
            embedding=embedding,
        )

    async def search_similar(
        self,
        embedding: list[float],
        *,
        reference_type: str | None = None,
        top_k: int = 5,
    ) -> list[VectorDocument]:
        """코사인 유사도 기반 유사 문서 검색 (pgvector)"""
        from tortoise import connections    # `connections`는 Tortoise ORM의 DB 연결 관리자. Tortoise ORM이 지원하지 않는 pgvector 연산자 (<=>)를 쓰려면 raw SQL이 필요해서 직업 연결을 가져온.

        conn = connections.get("default")
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"    # pgvector가 인식하는 벡터 문자열 포맷으로 변환. [0.12, 0.87, ...] 형태의 문자열이 되어야 함. $1::vector로 캐스팅할 때 이 포맷이 필요
        
        if reference_type:  # 버그의 핵심. 기존 코드는 where / limit_param 변수를 f-string으로 조합했는데, $2/ $3 번호가 경우에 따라 달라지니까 SQL을 아예 분리하는게 명확함
            sql = """
            SELECT id , reference_type, reference_id, content, embedding, created_at
            FROM vector_documents
            WHERE reference_type = $2
            ORDER BY embedding::vector <=> $1::vector
            LIMIT $3
            """  # noqa: S608
            params = [vector_str, reference_type, top_k] # reference_type이 있을 때: $1=vector, $2=reference_type, $3=top_k순서로 매핑
        else:
            sql = """
            SELECT id , reference_type, reference_id, content, embedding, created_at
            FROM vector_documents
            ORDER BY embedding::vector <=> $1::vector
            LIMIT $2
            """  # noqa: S608
            params = [vector_str, top_k] # reference_type이 없을 때: $1=vector, $2=top_k. 파라미터가 하나 줄어서 번호도 달라짐
        rows = await conn.execute_query_dict(sql, params)   # execute_query_dict()는 결과를 list[dict] 형태로 반환. 이후 루프에서 VectorDocument 객체로 반환

        docs = []
        for row in rows:
            doc = VectorDocument(
                id=row["id"],
                reference_type=row["reference_type"],
                reference_id=row["reference_id"],
                content=row["content"],
                embedding=row["embedding"],
                created_at=row["created_at"],
            )
            docs.append(doc)
        return docs

    async def delete_by_reference(self, reference_type: str, reference_id: int) -> int:
        """삭제된 행 수 반환"""
        result = await self._model.filter(
            reference_type=reference_type,
            reference_id=reference_id,
        ).delete()
        return result
