-- pgvector 확장 활성화 (벡터 유사도 검색용)
-- vector_documents.embedding 컬럼에서 사용
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- HNSW 인덱스: 벡터 유사도 검색 성능 최적화 (full scan → ANN)
CREATE INDEX IF NOT EXISTS idx_vector_documents_embedding_hnsw
ON vector_documents USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
