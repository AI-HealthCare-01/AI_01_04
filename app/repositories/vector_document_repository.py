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
        from tortoise import connections

        conn = connections.get("default")
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"
        where = "WHERE reference_type = $2" if reference_type else ""
        params: list = [vector_str, top_k]
        if reference_type:
            params = [vector_str, reference_type, top_k]
            where = "WHERE reference_type = $2"
            limit_param = "$3"
        else:
            limit_param = "$2"

        sql = f"""
            SELECT id, reference_type, reference_id, content, embedding, created_at
            FROM vector_documents
            {where}
            ORDER BY embedding::vector <=> $1::vector
            LIMIT {limit_param}
        """  # noqa: S608
        rows = await conn.execute_query_dict(sql, params)
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
