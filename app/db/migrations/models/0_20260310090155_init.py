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
    "phone_number" VARCHAR(11) NOT NULL,
    "birthday" DATE NOT NULL,
    "gender" VARCHAR(6),
    "is_active" BOOL NOT NULL DEFAULT True,
    "is_admin" BOOL NOT NULL DEFAULT False,
    "profile_image_url" VARCHAR(500),
    "last_login" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON COLUMN "users"."gender" IS 'MALE: MALE\nFEMALE: FEMALE';
COMMENT ON TABLE "users" IS '사용자 모델 (ERD: users)';
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
CREATE TABLE IF NOT EXISTS "medication_intake_logs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "intake_date" DATE NOT NULL,
    "slot_label" VARCHAR(30),
    "intake_datetime" TIMESTAMPTZ,
    "status" VARCHAR(50) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "prescription_id" INT NOT NULL REFERENCES "prescriptions" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_medication__intake__dbfc1a" ON "medication_intake_logs" ("intake_date");
CREATE INDEX IF NOT EXISTS "idx_medication__intake__ccd0e0" ON "medication_intake_logs" ("intake_date", "status");
COMMENT ON TABLE "medication_intake_logs" IS '복용 기록 (ERD: medication_intake_logs)';
CREATE TABLE IF NOT EXISTS "prescription_memos" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "memo_datetime" TIMESTAMPTZ NOT NULL,
    "effect" TEXT,
    "side_effect" TEXT,
    "prescription_id" INT NOT NULL REFERENCES "prescriptions" ("id") ON DELETE CASCADE
);
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
    "embedding" vector(1536) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "vector_documents" IS '벡터 임베딩 문서 (ERD: vector_documents)';
CREATE TABLE IF NOT EXISTS "scans" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "status" VARCHAR(30) NOT NULL DEFAULT 'uploaded',
    "analyzed_at" TIMESTAMPTZ,
    "document_type" VARCHAR(30) NOT NULL DEFAULT 'prescription',
    "document_date" VARCHAR(10),
    "diagnosis" TEXT,
    "clinical_note" TEXT,
    "drugs" JSONB NOT NULL,
    "raw_text" TEXT,
    "ocr_raw" JSONB,
    "file_path" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_scans_user_id_ab3602" ON "scans" ("user_id", "id");
CREATE INDEX IF NOT EXISTS "idx_scans_user_id_5267cb" ON "scans" ("user_id", "created_at");
CREATE INDEX IF NOT EXISTS "idx_scans_user_id_c13a8f" ON "scans" ("user_id", "document_type");
COMMENT ON TABLE "scans" IS '의료문서 스캔 도메인 모델  # [CHANGED]';
CREATE TABLE IF NOT EXISTS "health_checklist_templates" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "label" VARCHAR(100) NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "sort_order" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "health_checklist_templates" IS '건강관리 체크리스트 템플릿(마스터)';
CREATE TABLE IF NOT EXISTS "health_checklist_logs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "date" DATE NOT NULL,
    "status" VARCHAR(20) NOT NULL,
    "checked_at" TIMESTAMPTZ,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "template_id" INT NOT NULL REFERENCES "health_checklist_templates" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_health_chec_date_ec545b" ON "health_checklist_logs" ("date");
CREATE INDEX IF NOT EXISTS "idx_health_chec_user_id_dac411" ON "health_checklist_logs" ("user_id", "date");
CREATE INDEX IF NOT EXISTS "idx_health_chec_date_bb2557" ON "health_checklist_logs" ("date", "status");
COMMENT ON TABLE "health_checklist_logs" IS '사용자 일자별 건강관리 로그';
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
    "scan_id" INT,
    "batch_id" INT NOT NULL REFERENCES "recommendation_batches" ("id") ON DELETE CASCADE,
    "feature_snapshot_id" INT REFERENCES "user_feature_snapshots" ("id") ON DELETE SET NULL,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_recommendat_scan_id_b607d8" ON "recommendations" ("scan_id");
CREATE INDEX IF NOT EXISTS "idx_recommendat_user_id_6e5d60" ON "recommendations" ("user_id", "scan_id");
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
)
