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
COMMENT ON TABLE "users" IS '사용자 모델 (ERD: users).';
CREATE TABLE IF NOT EXISTS "user_credentials" (
    "password_hash" VARCHAR(255) NOT NULL,
    "password_updated_at" TIMESTAMPTZ,
    "user_id" INT NOT NULL PRIMARY KEY REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_credentials" IS '사용자 비밀번호 정보 (ERD: user_credentials).';
CREATE TABLE IF NOT EXISTS "user_auth_providers" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "provider" VARCHAR(50) NOT NULL,
    "provider_user_id" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_auth_providers" IS '소셜 로그인 연동 정보 (ERD: user_auth_providers).';
CREATE TABLE IF NOT EXISTS "diseases" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "kcd_code" VARCHAR(20),
    "description" TEXT
);
COMMENT ON TABLE "diseases" IS '질병 마스터 테이블 (ERD: diseases).';
CREATE TABLE IF NOT EXISTS "disease_code_mappings" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "code" VARCHAR(20) NOT NULL UNIQUE,
    "name" VARCHAR(255) NOT NULL,
    "mapped_code" VARCHAR(20) NOT NULL,
    "mapped_name" VARCHAR(255) NOT NULL,
    "is_anchor" BOOL NOT NULL DEFAULT False
);
CREATE INDEX IF NOT EXISTS "idx_disease_cod_mapped__ddec1c" ON "disease_code_mappings" ("mapped_code");
COMMENT ON TABLE "disease_code_mappings" IS '상세 KCD 코드 → 추천 anchor 코드 매핑 테이블.';
CREATE TABLE IF NOT EXISTS "disease_guidelines" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "category" VARCHAR(100) NOT NULL,
    "content" TEXT NOT NULL,
    "source" VARCHAR(100),
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "disease_id" INT NOT NULL REFERENCES "diseases" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "disease_guidelines" IS '질병별 가이드라인 (ERD: disease_guidelines).';
CREATE TABLE IF NOT EXISTS "drugs" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(500) NOT NULL,
    "manufacturer" VARCHAR(255),
    "raw_material" TEXT,
    "raw_material_en" TEXT,
    "efficacy" TEXT,
    "dosage" TEXT,
    "caution_1" TEXT,
    "caution_2" TEXT,
    "caution_3" TEXT,
    "caution_4" TEXT,
    "storage" TEXT,
    "change_log" TEXT,
    "main_ingredient" TEXT,
    "edi_code" VARCHAR(255)
);
CREATE INDEX IF NOT EXISTS "idx_drugs_edi_cod_ed6393" ON "drugs" ("edi_code");
COMMENT ON TABLE "drugs" IS '약품 마스터 테이블 (ERD: drugs).';
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
COMMENT ON TABLE "prescriptions" IS '처방전 모델 (ERD: prescriptions).';
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
COMMENT ON TABLE "medication_intake_logs" IS '복용 기록 (ERD: medication_intake_logs).';
CREATE TABLE IF NOT EXISTS "prescription_memos" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "memo_datetime" TIMESTAMPTZ NOT NULL,
    "effect" TEXT,
    "side_effect" TEXT,
    "prescription_id" INT NOT NULL REFERENCES "prescriptions" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "prescription_memos" IS '복약 메모 (ERD: prescription_memos).';
CREATE TABLE IF NOT EXISTS "medi_chat" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "patient_id" VARCHAR(50) NOT NULL,
    "disease_code" VARCHAR(20),
    "medications" TEXT,
    "advice" TEXT,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_medi_chat_patient_774dc3" ON "medi_chat" ("patient_id");
CREATE TABLE IF NOT EXISTS "health_chat" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "patient_id" VARCHAR(50) NOT NULL,
    "user_question" TEXT NOT NULL,
    "advice" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS "idx_health_chat_patient_53559b" ON "health_chat" ("patient_id");
CREATE TABLE IF NOT EXISTS "chatbot_sessions" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "started_at" TIMESTAMPTZ,
    "ended_at" TIMESTAMPTZ,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "chatbot_sessions" IS '챗봇 대화 세션 (ERD: chatbot_sessions).';
CREATE TABLE IF NOT EXISTS "chatbot_messages" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "sender" VARCHAR(20) NOT NULL,
    "message" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "session_id" INT NOT NULL REFERENCES "chatbot_sessions" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "chatbot_messages" IS '챗봇 메시지 (ERD: chatbot_messages).';
CREATE TABLE IF NOT EXISTS "chatbot_session_summaries" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "summary" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "session_id" INT NOT NULL REFERENCES "chatbot_sessions" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "chatbot_session_summaries" IS '세션 요약 (ERD: chatbot_session_summaries).';
CREATE TABLE IF NOT EXISTS "vector_documents" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "reference_type" VARCHAR(100) NOT NULL,
    "reference_id" INT NOT NULL,
    "content" TEXT NOT NULL,
    "embedding" TEXT NOT NULL,
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
    "diagnosis_list" JSONB NOT NULL,
    "clinical_note" TEXT,
    "error_message" TEXT,
    "drugs" JSONB NOT NULL,
    "unrecognized_drugs" JSONB NOT NULL,
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
COMMENT ON TABLE "scans" IS '의료문서 스캔 도메인 모델 (ERD: scans).';
CREATE TABLE IF NOT EXISTS "health_checklist_templates" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "label" VARCHAR(100) NOT NULL,
    "is_active" BOOL NOT NULL DEFAULT True,
    "sort_order" INT NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE "health_checklist_templates" IS '건강관리 체크리스트 템플릿 (마스터).';
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
COMMENT ON TABLE "health_checklist_logs" IS '사용자 일자별 건강관리 로그.';
CREATE TABLE IF NOT EXISTS "user_current_features" (
    "feature_json" TEXT NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL PRIMARY KEY REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_current_features" IS '사용자 현재 피처 (ERD: user_current_features).';
CREATE TABLE IF NOT EXISTS "user_feature_snapshots" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "feature_json" TEXT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_feature_snapshots" IS '사용자 피처 스냅샷 (ERD: user_feature_snapshots).';
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
COMMENT ON TABLE "recommendation_batches" IS '추천 배치 (ERD: recommendation_batches).';
CREATE TABLE IF NOT EXISTS "recommendations" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "recommendation_type" VARCHAR(50),
    "source" VARCHAR(100),
    "content" TEXT,
    "frequency" VARCHAR(30),
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
COMMENT ON TABLE "recommendations" IS '개별 추천 결과 (ERD: recommendations).';
CREATE TABLE IF NOT EXISTS "recommendation_feedback" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "feedback_type" VARCHAR(50) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "recommendation_id" INT NOT NULL REFERENCES "recommendations" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "recommendation_feedback" IS '추천 피드백 (ERD: recommendation_feedback).';
CREATE TABLE IF NOT EXISTS "user_active_recommendations" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "assigned_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "recommendation_id" INT NOT NULL REFERENCES "recommendations" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
COMMENT ON TABLE "user_active_recommendations" IS '사용자 활성 추천 (ERD: user_active_recommendations).';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
