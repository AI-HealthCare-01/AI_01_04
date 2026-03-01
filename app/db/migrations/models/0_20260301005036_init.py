from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "users" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "email" VARCHAR(40) NOT NULL UNIQUE,
    "name" VARCHAR(100) NOT NULL,
    "nickname" VARCHAR(50),
    "phone_number" VARCHAR(11) NOT NULL,
    "birth_date" DATE,
    "gender" VARCHAR(6),
    "role" VARCHAR(5) NOT NULL DEFAULT 'USER',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "users"."gender" IS 'MALE: MALE\nFEMALE: FEMALE';
COMMENT ON COLUMN "users"."role" IS 'USER: USER\nADMIN: ADMIN';
COMMENT ON TABLE "users" IS '사용자 테이블 (ERD: users)';
CREATE TABLE IF NOT EXISTS "user_credentials" (
    "password_hash" VARCHAR(255) NOT NULL,
    "password_updated_at" TIMESTAMPTZ,
    "user_id" INT NOT NULL PRIMARY KEY REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_credentials" IS '사용자 비밀번호 정보 (ERD: user_credentials)';
CREATE TABLE IF NOT EXISTS "user_auth_providers" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "provider" VARCHAR(50) NOT NULL,
    "provider_user_id" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_auth_providers" IS '소셜 로그인 연동 정보 (ERD: user_auth_providers)';
CREATE TABLE IF NOT EXISTS "diseases" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "icd_code" VARCHAR(20),
    "description" TEXT
);
COMMENT ON TABLE "diseases" IS '질병 마스터 테이블 (ERD: diseases)';
CREATE TABLE IF NOT EXISTS "disease_guidelines" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "category" VARCHAR(100) NOT NULL,
    "content" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "disease_id" INT NOT NULL REFERENCES "diseases" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "disease_guidelines" IS '질병별 가이드라인 (ERD: disease_guidelines)';
CREATE TABLE IF NOT EXISTS "drugs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "manufacturer" VARCHAR(255)
);
COMMENT ON TABLE "drugs" IS '약품 마스터 테이블 (ERD: drugs)';
CREATE TABLE IF NOT EXISTS "prescriptions" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "dose_count" INT,
    "dose_amount" VARCHAR(50),
    "dose_unit" VARCHAR(20),
    "start_date" DATE,
    "end_date" DATE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "disease_id" INT REFERENCES "diseases" ("id") ON DELETE SET NULL,
    "drug_id" INT REFERENCES "drugs" ("id") ON DELETE SET NULL,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "prescriptions" IS '처방전 테이블 (ERD: prescriptions)';
CREATE TABLE IF NOT EXISTS "medication_intake_logs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "intake_datetime" TIMESTAMPTZ NOT NULL,
    "status" VARCHAR(50) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "prescription_id" INT NOT NULL REFERENCES "prescriptions" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "medication_intake_logs" IS '복용 기록 (ERD: medication_intake_logs)';
CREATE TABLE IF NOT EXISTS "prescription_memos" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "memo_datetime" TIMESTAMPTZ NOT NULL,
    "effect" TEXT,
    "side_effect" TEXT,
    "prescription_id" INT NOT NULL REFERENCES "prescriptions" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "prescription_memos" IS '처방전 메모 (ERD: prescription_memos)';
CREATE TABLE IF NOT EXISTS "chatbot_sessions" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "started_at" TIMESTAMPTZ,
    "ended_at" TIMESTAMPTZ,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "chatbot_sessions" IS '챗봇 대화 세션 (ERD: chatbot_sessions)';
CREATE TABLE IF NOT EXISTS "chatbot_messages" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "sender" VARCHAR(20) NOT NULL,
    "message" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "session_id" INT NOT NULL REFERENCES "chatbot_sessions" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "chatbot_messages" IS '챗봇 메시지 (ERD: chatbot_messages)';
CREATE TABLE IF NOT EXISTS "chatbot_session_summaries" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "summary" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "session_id" INT NOT NULL REFERENCES "chatbot_sessions" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "chatbot_session_summaries" IS '세션 요약 (ERD: chatbot_session_summaries)';
CREATE TABLE IF NOT EXISTS "vector_documents" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "reference_type" VARCHAR(100) NOT NULL,
    "reference_id" INT NOT NULL,
    "content" TEXT NOT NULL,
    "embedding" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "vector_documents" IS '벡터 임베딩 문서 (ERD: vector_documents)';
CREATE TABLE IF NOT EXISTS "user_current_features" (
    "feature_json" TEXT NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL PRIMARY KEY REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_current_features" IS '사용자 현재 피처 (ERD: user_current_features)';
CREATE TABLE IF NOT EXISTS "user_feature_snapshots" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "feature_json" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_feature_snapshots" IS '사용자 피처 스냅샷 (ERD: user_feature_snapshots)';
CREATE TABLE IF NOT EXISTS "recommendation_batches" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "retrieval_strategy" VARCHAR(100),
    "retrieval_top_k" INT,
    "retrieval_lambda" DOUBLE PRECISION,
    "llm_model" VARCHAR(100),
    "llm_temperature" DOUBLE PRECISION,
    "llm_max_tokens" INT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "recommendation_batches" IS '추천 배치 (ERD: recommendation_batches)';
CREATE TABLE IF NOT EXISTS "recommendations" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "recommendation_type" VARCHAR(50),
    "source" VARCHAR(100),
    "content" TEXT,
    "score" DOUBLE PRECISION,
    "is_selected" BOOL,
    "rank" INT,
    "status" VARCHAR(50),
    "model_version" VARCHAR(50),
    "prompt_version" VARCHAR(50),
    "embedding_model_version" VARCHAR(50),
    "expiration_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "batch_id" INT NOT NULL REFERENCES "recommendation_batches" ("id") ON DELETE CASCADE,
    "feature_snapshot_id" INT REFERENCES "user_feature_snapshots" ("id") ON DELETE SET NULL,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "recommendations" IS '개별 추천 결과 (ERD: recommendations)';
CREATE TABLE IF NOT EXISTS "recommendation_feedback" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "feedback_type" VARCHAR(50) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "recommendation_id" INT NOT NULL REFERENCES "recommendations" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "recommendation_feedback" IS '추천 피드백 (ERD: recommendation_feedback)';
CREATE TABLE IF NOT EXISTS "user_active_recommendations" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "assigned_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "recommendation_id" INT NOT NULL REFERENCES "recommendations" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_active_recommendations" IS '사용자 활성 추천 (ERD: user_active_recommendations)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "BgR7o="
)
