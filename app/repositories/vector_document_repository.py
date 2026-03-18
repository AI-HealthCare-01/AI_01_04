"""
벡터 문서 도메인 Repository

- VectorDocument: reference_type + reference_id로 다형 참조 (user_id 없음)
- user 스코프: reference가 user 소유인지는 서비스 레이어에서 검증
- 이 레포는 reference 기반 CRUD 제공, 서비스에서 user 소유 reference만 전달
"""

from __future__ import annotations

from app.models.vector_documents import VectorDocument


class VectorDocumentRepository:
    """
    vector_documents 테이블 접근을 담당하는 Repository.
    """

    def __init__(self):
        self._model = VectorDocument

    async def get_by_id(self, doc_id: int) -> VectorDocument | None:
        """
        문서 ID로 벡터 문서 1건을 조회한다.

        Args:
            doc_id (int):
                벡터 문서 ID

        Returns:
            VectorDocument | None:
                조회된 벡터 문서 객체
        """
        return await self._model.get_or_none(id=doc_id)

    async def get_by_reference(
        self,
        reference_type: str,
        reference_id: int,
    ) -> VectorDocument | None:
        """
        reference_type + reference_id 조합으로 벡터 문서를 조회한다.

        Args:
            reference_type (str):
                참조 타입
            reference_id (int):
                참조 ID

        Returns:
            VectorDocument | None:
                조회된 벡터 문서 객체
        """
        return await self._model.get_or_none(
            reference_type=reference_type,
            reference_id=reference_id,
        )

    async def list_by_reference_type_and_ids(
        self,
        reference_type: str,
        reference_ids: list[int],
    ) -> list[VectorDocument]:
        """
        동일한 reference_type과 여러 reference_id에 해당하는 벡터 문서를 조회한다.

        Args:
            reference_type (str):
                참조 타입
            reference_ids (list[int]):
                참조 ID 목록

        Returns:
            list[VectorDocument]:
                조회된 벡터 문서 목록
        """
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
        """
        벡터 문서를 생성한다.

        Args:
            reference_type (str):
                참조 타입
            reference_id (int):
                참조 ID
            content (str):
                원문 내용
            embedding (list[float]):
                임베딩 벡터

        Returns:
            VectorDocument:
                생성된 벡터 문서 객체
        """
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
        """
        pgvector 코사인 거리 연산으로 유사 문서를 검색한다.

        Args:
            embedding (list[float]):
                검색 기준 임베딩 벡터
            reference_type (str | None):
                특정 reference_type으로 필터링할지 여부
            top_k (int):
                반환할 최대 문서 수

        Returns:
            list[VectorDocument]:
                유사한 벡터 문서 목록
        """
        from tortoise import connections

        conn = connections.get("default")
        vector_str = "[" + ",".join(str(v) for v in embedding) + "]"

        if reference_type:
            sql = """
            SELECT id, reference_type, reference_id, content, embedding, created_at,
                   embedding::vector <=> $1::vector AS distance
            FROM vector_documents
            WHERE reference_type = $2
            ORDER BY distance
            LIMIT $3
            """  # noqa: S608
            params = [vector_str, reference_type, top_k]
        else:
            sql = """
            SELECT id, reference_type, reference_id, content, embedding, created_at,
                   embedding::vector <=> $1::vector AS distance
            FROM vector_documents
            ORDER BY distance
            LIMIT $2
            """  # noqa: S608
            params = [vector_str, top_k]

        rows = await conn.execute_query_dict(sql, params)

        docs: list[VectorDocument] = []
        for row in rows:
            doc = VectorDocument(
                id=row["id"],
                reference_type=row["reference_type"],
                reference_id=row["reference_id"],
                content=row["content"],
                embedding=row["embedding"],
                created_at=row["created_at"],
            )
            doc._distance = float(row["distance"])  # type: ignore[attr-defined]
            docs.append(doc)

        return docs

    async def search_drug_context(
        self,
        embedding: list[float],
        *,
        top_k: int = 5,
    ) -> list[VectorDocument]:
        """drug 관련 벡터 문서만 검색한다. 결과가 없으면 전체에서 fallback."""
        docs = await self.search_similar(embedding, reference_type="drug", top_k=top_k)
        if not docs:
            docs = await self.search_similar(embedding, top_k=top_k)
        return docs

    async def search_disease_context(
        self,
        embedding: list[float],
        *,
        top_k: int = 5,
    ) -> list[VectorDocument]:
        """disease_guideline 관련 벡터 문서만 검색한다."""
        return await self.search_similar(embedding, reference_type="disease_guideline", top_k=top_k)

    async def search_with_type_priority(
        self,
        embedding: list[float],
        *,
        preferred_type: str,
        top_k: int = 5,
        fallback_threshold: float = 0.5,
    ) -> list[VectorDocument]:
        """preferred_type을 우선 검색하고, 유사도가 낮으면 전체에서 보충한다."""
        docs = await self.search_similar(embedding, reference_type=preferred_type, top_k=top_k)

        # 유사도가 threshold 이상인 문서만 유지
        good_docs = [d for d in docs if hasattr(d, "_distance") and d._distance < fallback_threshold]

        if len(good_docs) < top_k:
            all_docs = await self.search_similar(embedding, top_k=top_k)
            seen_ids = {d.id for d in good_docs}
            for d in all_docs:
                if d.id not in seen_ids and len(good_docs) < top_k:
                    good_docs.append(d)
                    seen_ids.add(d.id)

        return good_docs

    async def delete_by_reference(self, reference_type: str, reference_id: int) -> int:
        """
        reference_type + reference_id 조합으로 벡터 문서를 삭제한다.

        Args:
            reference_type (str):
                참조 타입
            reference_id (int):
                참조 ID

        Returns:
            int:
                삭제된 행 수
        """
        return await self._model.filter(
            reference_type=reference_type,
            reference_id=reference_id,
        ).delete()
